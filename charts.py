import plotly.express as px
import duckdb as ddb
from preprocess import fifa_data

def plot_bar_graph(query , x_axis, y_axis):
    df = ddb.query(query).df()
    fig = px.bar(
    df,
    x=x_axis,
    y=y_axis,
    )

    return fig.to_html()

def route_chart_calling(query, x_axis, y_axis, chart_type = "Bar"):
    if chart_type == "Bar":
        return plot_bar_graph(query,x_axis,y_axis)
