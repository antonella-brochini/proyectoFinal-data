from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime


PROJECT_PATH = "/opt/proyecto"


with DAG(
    dag_id="superstore_pipeline",
    start_date=datetime(2026, 7, 9),
    schedule="@daily",
    catchup=False,
    description="Pipeline completo de análisis Superstore",
) as dag:


    analyze_data = BashOperator(
        task_id="profile_raw_dataset",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/analyze_data.py > logs/analyze_data_output.txt
        """
    )


    data_cleaning = BashOperator(
        task_id="clean_validate_engineer",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/data_cleaning.py
        """
    )


    db_import = BashOperator(
        task_id="import_database",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/db_import.py
        """
    )


    showcase = BashOperator(
        task_id="generate_charts",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/showcase.py
        """
    )


    advanced_analytics = BashOperator(
        task_id="advanced_analytics",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/advanced_analytics.py
        """
    )


    interactive_dashboard = BashOperator(
        task_id="interactive_dashboard",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/interactive_dashboard.py
        """
    )


    export_html = BashOperator(
        task_id="export_html_dashboard",
        bash_command=f"""
        cd {PROJECT_PATH} &&
        python scripts/export_html.py
        """
    )


    (
        analyze_data
        >> data_cleaning
        >> db_import
        >> showcase
        >> advanced_analytics
        >> interactive_dashboard
        >> export_html
    )