import dash
from dash import html, callback, Input, Output
import dash_bootstrap_components as dbc

from front import import_view, parameters_view, optimize_view


# APPLICATION SETUP
# ------------------------------------
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = 'Alto Scheduler'

# LAYOUT
app.layout = html.Div(
    children=[
        dbc.NavbarSimple(
            brand="Alto: Schedule Optimization",
            color="primary",
            dark=True,
        ),
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Import Data", tab_id="tab-1"),
                            dbc.Tab(label="Set Model Parameters", tab_id="tab-2"),
                            dbc.Tab(label="Optimize", tab_id="tab-4"),
                        ],
                        id="card-tabs"
                    )
                ),
                dbc.CardBody(html.P(id="card-content", className="card-text")),
            ]
        )
    ],
)

@callback(
    Output("card-content", "children"), [Input("card-tabs", "active_tab")]
)
def tab_content(active_tab):
    if active_tab == 'tab-1':
        return import_view.layout
    elif active_tab == 'tab-2':
        return parameters_view.layout
    elif active_tab == 'tab-4':
        return optimize_view.layout
    else:
        return import_view.layout


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8080, use_reloader=False)
