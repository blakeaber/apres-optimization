# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc

import front.forecast_view as fv

app = Dash(__name__)

app.layout = html.Div(
    children=[
        html.H1(children="Alto App"),
        html.Div(
            children=dcc.Tabs(
                [
                    dcc.Tab(
                        label="Forecast",
                        children=fv.layout,
                    )
                ]
            ),
        ),
    ]
)

if __name__ == "__main__":
    app.run_server(debug=True)
