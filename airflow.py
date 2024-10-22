AIRFLOW_VERSION="2.10.2"

# Extract the version of Python you have installed. If you're currently using a Python version that is not supported by Airflow, you may want to set this manually.
# See above for supported versions.
import subprocess

PYTHON_VERSION = subprocess.check_output(["python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"]).decode().strip()

CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"
# For example this would install 2.10.2 with python 3.8: https://raw.githubusercontent.com/apache/airflow/constraints-2.10.2/constraints-3.8.txt

# Run the following command in your terminal to install Apache Airflow with the specified constraints
# pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"