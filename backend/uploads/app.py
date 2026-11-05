import os
import math
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
from langchain_groq import ChatGroq
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Backend is running'})

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

current_df = None
current_filename = None


def _format_report_value(value):
    if pd.isna(value):
        return 'N/A'
    if isinstance(value, (int, float)):
        return f'{value:,.3f}'.rstrip('0').rstrip('.')
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _column_kind(name, series):
    if pd.api.types.is_bool_dtype(series):
        return 'Boolean'
    if pd.api.types.is_numeric_dtype(series):
        return 'Numeric'
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'Date/time'

    values = series.dropna()
    if len(values) and not pd.api.types.is_numeric_dtype(series):
        sample = values.astype(str).head(1000)
        date_name = any(
            word in str(name).lower()
            for word in ('date', 'time', 'timestamp', 'created', 'updated')
        )
        date_pattern = sample.str.contains(
            r'\d{1,4}[-/:]\d{1,2}[-/:]\d{1,4}', regex=True
        ).mean()
        if not date_name and date_pattern < 0.8:
            return 'Categorical'
        parsed = pd.to_datetime(sample, format='mixed', errors='coerce', utc=True)
        if parsed.notna().mean() >= (0.8 if date_name else 0.95):
            return 'Date/time'
    if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype):
        return 'Categorical'
    return 'Other'


def build_analysis_report(dataframe, filename):
    row_count, column_count = dataframe.shape
    total_cells = row_count * column_count
    missing_cells = int(dataframe.isna().sum().sum())
    duplicate_rows = int(dataframe.duplicated().sum())
    kinds = {column: _column_kind(column, dataframe[column]) for column in dataframe.columns}
    kind_counts = pd.Series(list(kinds.values())).value_counts()
    missing_percent = missing_cells / total_cells * 100 if total_cells else 0
    duplicate_percent = duplicate_rows / row_count * 100 if row_count else 0

    lines = [
        f'# Complete Data Analysis Report: {_format_report_value(filename)}',
        '',
        '## Executive summary',
        f'- **Dataset size:** {row_count:,} rows and {column_count:,} columns.',
        f'- **Column types:** {int(kind_counts.get("Numeric", 0))} numeric, '
        f'{int(kind_counts.get("Categorical", 0))} categorical, '
        f'{int(kind_counts.get("Date/time", 0))} date/time, '
        f'{int(kind_counts.get("Boolean", 0))} boolean.',
        f'- **Missing data:** {missing_cells:,} of {total_cells:,} cells '
        f'({missing_percent:.1f}%).',
        f'- **Duplicate rows:** {duplicate_rows:,} ({duplicate_percent:.1f}% of rows).',
        '',
        '## Data quality',
        '| Column | Type | Missing | Missing % | Distinct values |',
        '|---|---|---:|---:|---:|',
    ]

    if column_count:
        for column in dataframe.columns:
            series = dataframe[column]
            missing = int(series.isna().sum())
            distinct = int(series.nunique(dropna=True))
            percent = missing / row_count * 100 if row_count else 0
            lines.append(
                f'| {_format_report_value(column)} | {kinds[column]} | {missing:,} '
                f'| {percent:.1f}% | {distinct:,} |'
            )
    else:
        lines.append('| No columns | — | — | — | — |')
    if duplicate_rows:
        lines.extend([
            '',
            f'**Finding:** {duplicate_rows:,} rows are exact duplicates. Review them '
            'before analysis if each row is expected to represent a unique record.',
        ])
    if missing_cells:
        lines.extend([
            '',
            '**Finding:** Missing values are present. Review the per-column counts '
            'above before choosing whether to impute or exclude values.',
        ])
    else:
        lines.extend(['', '**Finding:** No missing cells were detected.'])

    numeric_columns = [column for column in dataframe.columns if kinds[column] == 'Numeric']
    lines.extend([
        '',
        '## Numeric column summaries',
    ])
    if numeric_columns:
        lines.extend([
            '| Column | Valid values | Mean | Median | Std. dev. | Min | Q1 | Q3 | Max | IQR outliers |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
        ])
        for column in numeric_columns:
            values = pd.to_numeric(dataframe[column], errors='coerce')
            values = values[values.map(lambda value: math.isfinite(value) if pd.notna(value) else False)]
            if values.empty:
                lines.append(f'| {_format_report_value(column)} | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0 |')
                continue
            q1, median, q3 = values.quantile([0.25, 0.5, 0.75]).tolist()
            iqr = q3 - q1
            outliers = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
            stats = [
                len(values), values.mean(), median, values.std(), values.min(),
                q1, q3, values.max(), outliers,
            ]
            formatted = [_format_report_value(value) for value in stats]
            lines.append(f'| {_format_report_value(column)} | ' + ' | '.join(formatted) + ' |')
    else:
        lines.append('No numeric columns were detected.')

    lines.extend(['', '## Numeric distributions'])
    chart_columns = [
        column for column in numeric_columns
        if dataframe[column].nunique(dropna=True) > 1
    ][:6]
    if chart_columns:
        for column in chart_columns:
            values = pd.to_numeric(dataframe[column], errors='coerce')
            values = values[values.map(lambda value: math.isfinite(value) if pd.notna(value) else False)]
            bins = min(8, int(values.nunique()))
            counts = pd.cut(values, bins=bins, include_lowest=True).value_counts(sort=False)
            max_count = max(counts.max(), 1)
            lines.extend([
                f'**{_format_report_value(column)}**',
                '```text',
            ])
            for interval, count in counts.items():
                bar = '#' * max(1, round(count / max_count * 20)) if count else ''
                lines.append(f'{str(interval):>28} | {bar} {count:,}')
            lines.append('```')
    else:
        lines.append('No numeric columns with varying values are available to plot.')

    categorical_columns = [column for column in dataframe.columns if kinds[column] == 'Categorical']
    lines.extend(['', '## Categorical column summaries'])
    if categorical_columns:
        for column in categorical_columns:
            series = dataframe[column]
            counts = series.value_counts(dropna=True).head(5)
            lines.append(
                f'- **{_format_report_value(column)}** ({series.nunique(dropna=True):,} '
                'distinct values): '
            )
            if counts.empty:
                lines.append('  - No non-missing values.')
            else:
                lines.append(
                    ', '.join(
                        f'{_format_report_value(value)} ({count:,}, '
                        f'{count / max(1, int(series.notna().sum())) * 100:.1f}%)'
                        for value, count in counts.items()
                    )
                )
    else:
        lines.append('No categorical columns were detected.')

    date_columns = [column for column in dataframe.columns if kinds[column] == 'Date/time']
    lines.extend(['', '## Date/time coverage'])
    if date_columns:
        for column in date_columns:
            dates = pd.to_datetime(dataframe[column], errors='coerce', utc=True).dropna()
            if dates.empty:
                lines.append(f'- **{_format_report_value(column)}:** no parseable dates.')
            else:
                lines.append(
                    f'- **{_format_report_value(column)}:** {len(dates):,} parseable '
                    f'values spanning {dates.min().date()} to {dates.max().date()}.'
                )
    else:
        lines.append('No date/time columns were detected.')

    lines.extend(['', '## Relationships and notable patterns'])
    if len(numeric_columns) >= 2 and row_count >= 2:
        correlations = dataframe[numeric_columns].replace(
            [float('inf'), float('-inf')], float('nan')
        ).corr()
        pairs = []
        for index, first in enumerate(numeric_columns):
            for second in numeric_columns[index + 1:]:
                correlation = correlations.loc[first, second]
                if pd.notna(correlation):
                    pairs.append((abs(correlation), correlation, first, second))
        pairs.sort(reverse=True)
        if pairs:
            lines.extend([
                '| Numeric pair | Pearson correlation |',
                '|---|---:|',
            ])
            for _, correlation, first, second in pairs[:10]:
                lines.append(
                    f'| {_format_report_value(first)} / {_format_report_value(second)} '
                    f'| {correlation:.3f} |'
                )
            lines.append(
                'Correlations describe linear association and do not establish causation.'
            )
        else:
            lines.append('No usable pairwise numeric correlations could be calculated.')
    else:
        lines.append('At least two numeric columns with sufficient values are needed to calculate correlations.')

    recommendations = []
    if missing_cells:
        recommendations.append('Investigate missingness by column and decide on treatment using the data context.')
    if duplicate_rows:
        recommendations.append('Check whether exact duplicate rows are valid repeated events or ingestion duplicates.')
    if any(kinds[column] == 'Numeric' for column in numeric_columns):
        outlier_columns = []
        for column in numeric_columns:
            values = pd.to_numeric(dataframe[column], errors='coerce')
            values = values[values.map(lambda value: math.isfinite(value) if pd.notna(value) else False)]
            if len(values) >= 4:
                q1, q3 = values.quantile([0.25, 0.75]).tolist()
                iqr = q3 - q1
                count = int(((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)).sum())
                if count:
                    outlier_columns.append(f'{_format_report_value(column)} ({count:,})')
        if outlier_columns:
            recommendations.append('Review IQR-flagged values for potential outliers: ' + ', '.join(outlier_columns) + '.')
    if not recommendations:
        recommendations.append('No immediate missing-value or duplicate-row issues were detected; validate the fields against their business definitions.')
    lines.extend(['', '## Recommended next steps'])
    lines.extend(f'{index}. {recommendation}' for index, recommendation in enumerate(recommendations, start=1))
    lines.extend([
        '',
        '> This report describes the uploaded data. Outlier flags are screening signals, '
        'not proof of errors; correlation is not causation. No predictive model was '
        'trained because a target and forecasting/classification goal were not specified.',
    ])
    return '\n'.join(lines)

def get_llm():
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured. Please set it in the .env file.")
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model_name="qwen/qwen3.8-27b",
        temperature=0.1,
        max_tokens=512,
        )
@app.route('/api/upload', methods=['POST'])
def upload_file():
    global current_df, current_filename
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({'error': 'Invalid filename'}), 400
    extension = filename.rsplit('.', 1)[-1].lower()
    if extension not in {'csv', 'xlsx', 'xls'}:
        return jsonify({'error': 'Unsupported file format'}), 400
    try:
        file_data = BytesIO(file.read())
        if extension == 'csv':
            dataframe = pd.read_csv(file_data)
        else:
            dataframe = pd.read_excel(file_data)
        summary = {
            'filename': filename,
            'rows': int(dataframe.shape[0]),
            'columns': int(dataframe.shape[1]),
            'columns_names': dataframe.columns.tolist(),
            'preview': dataframe.head(5).fillna('').to_dict(orient='records')
        }
        current_df = dataframe
        current_filename = filename
        return jsonify({'message':'file uploaded successfully','summary':summary}), 200
    except Exception as e:
        return jsonify({'error':f'Failed to parse file: {str(e)}'}), 500

@app.route('/api/upload', methods=['DELETE'])
def delete_upload():
    global current_df, current_filename
    current_df = None
    current_filename = None
    return jsonify({'message': 'Uploaded dataset deleted'}), 200


@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    if current_df is None:
        return jsonify({'error': 'No file uploaded yet'}), 400
    try:
        report = build_analysis_report(current_df, current_filename or 'Uploaded dataset')
        return jsonify({'report': report}), 200
    except Exception as e:
        return jsonify({'error': f'Analysis error: {str(e)}'}), 500


@app.route('/api/query',methods=['post'])
def query_data():
    global current_df
    if current_df is None:
        return jsonify({'error':'No file uploaded yet'}),400
    data = request.get_json()
    user_query = data.get('query','')
    if not user_query:
        return jsonify({'error':'Query text cannot be empty'}),400
    try:
        llm = get_llm()
        agent = create_pandas_dataframe_agent(
            llm,
            current_df,
            agent_type="tool-calling",
            prefix=(
                "You are working with a pandas dataframe in Python named `df`. "
                "Use the dataframe tools to calculate answers from the uploaded data. "
                "Never invent values or claim a calculation you did not perform. "
                "Format analytical responses in clear Markdown: give a short direct "
                "answer first, then use a **Key findings** bullet list when there are "
                "multiple insights. Use a Markdown table when comparing several "
                "categories or metrics. Include a brief **Method** only when it helps "
                "explain the calculation. For simple questions, keep the answer concise."
            ),
            verbose = False,
            allow_dangerous_code=True
        )
        response = agent.invoke({"input": user_query})["output"]
        return jsonify({'query': user_query,'result':response})
    except Exception as e:
        return jsonify({'error':f'Execution error:{str(e)}'}),500

if __name__ == '__main__':
    app.run(debug=True, port=5000)