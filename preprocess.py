import pandas as pd
from os.path import dirname, abspath, join
import duckdb as ddb
import chatlas

fifa_all_data_file_name = "EAFC26.csv"

project_root = dirname(abspath(__file__))
data_folder = join(project_root, 'Data')
fifa_data_file = join(data_folder, fifa_all_data_file_name)

fifa_data = pd.read_csv(join(data_folder , fifa_all_data_file_name))
fifa_data = fifa_data.drop(columns = ['card', 'url', 'ID'])

ddb.register("fifa", fifa_data)