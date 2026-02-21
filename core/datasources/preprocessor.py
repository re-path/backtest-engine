
import os
import pandas as pd
from typing import Optional, List, Dict, Any, Union
from .duckdb_manager import DuckDBManager
from jinja2 import Template

class SQLPreprocessor:
    def __init__(self):
        self.manager = DuckDBManager.get_instance()

    def preprocess(self, sql_template: str, **kwargs) -> str:
        template = Template(sql_template)
        return template.render(**kwargs)

    def execute_query(self, sql_template: str, **kwargs) -> pd.DataFrame:
        optimized_sql = self.preprocess(sql_template, **kwargs)
        params = kwargs.get('_params', [])
        try:
            return self.manager.execute(optimized_sql, params).df()
        except Exception as e:
            raise e