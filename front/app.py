# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from dash import Dash, html, dcc

import front.forecast_view as fv

app = Dash(__name__)

# Tab CSS styling is bugged
tab_style = {
    "color": "white",
    "background-color": "#916a56",
    "align-items": "center",
    "justify-content": "center",
}

tab_selected_style = {
    "color": "#312b2b",
    "border-top": "3px solid #916a56",
}

app.layout = html.Div(
    children=[
        html.H1(children="Alto App", className="app-title"),
        html.Div(
            children=dcc.Tabs(
                [
                    dcc.Tab(
                        label="Forecast",
                        children=fv.layout,
                        style=tab_style,
                        selected_style=tab_selected_style,
                    ),
                    dcc.Tab(
                        label="Scheduling",
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                        style=tab_style,
                        selected_style=tab_selected_style,
                    ),
                ]
            ),
        ),
    ],
)

if __name__ == "__main__":
    app.run_server(debug=True)
