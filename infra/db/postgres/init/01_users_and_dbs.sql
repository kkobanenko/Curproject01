-- Users & DBs
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE USER superset WITH PASSWORD 'superset';

CREATE DATABASE airflow OWNER airflow;
CREATE DATABASE superset OWNER superset;
CREATE DATABASE rag_app OWNER postgres;
