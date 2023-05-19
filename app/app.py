# %% 
# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import plotly.express as px
import plotly.graph_objects as go
# %%
import dash_bootstrap_components as dbc

# %% 
import pandas as pd
nowcast = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/nowcast.csv")    # index_col="date", parse_dates=True
gdp_ld = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/gdp_logdiff.csv") # index_col="quarter", parse_dates=True
gdp_ld.index = pd.PeriodIndex(gdp_ld.quarter, freq="Q")
gdp_ld = gdp_ld.loc[gdp_ld.index >= pd.PeriodIndex(nowcast.quarter, freq="Q").min()]
news = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/news.csv")
series = pd.read_csv("https://raw.githubusercontent.com/Stellenbosch-Econometrics/SA-Nowcast/main/nowcast/series.csv")
news = news.merge(series, 
                  left_on = "updated variable", 
                  right_on = "series", how = "left")
# format this to month-day
q = nowcast.quarter.max()
nowcast_latest_quarter = nowcast.loc[nowcast.quarter == q]
nowcast_dates = dict(zip(nowcast_latest_quarter.date, 
                         pd.to_datetime(nowcast_latest_quarter.date).dt.strftime("%b-%d")))
all_nowcast_dates = list(nowcast.date)



# %%
nowcast_final = nowcast.copy()
nowcast_final.date = pd.to_datetime(nowcast_final.date)
final_ids = nowcast_final.groupby('quarter').date.idxmax()
nowcast_final = nowcast.iloc[final_ids] # nowcast.groupby("quarter").last().reset_index()
nowcast_other = nowcast.drop(index = final_ids)


# %% 
news["sector_topic"] = news.broad_sector + ": " + news.topic
# News digest
news_tot = news.groupby(["impacted variable", "sector_topic", "broad_sector", "topic"]) \
               .agg({"weight": "mean", "impact": "mean"}).reset_index() 
news_tot["abs_impact"] = news_tot.impact.abs() # * 100
news_tot.head()


# %% 
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG]) # QUARTZ


app.layout = dbc.Container([
    # html.Div(children='My First App with Data'),
    html.Br(),
    html.H3("South Africa Nowcast"),
    html.Hr(),
    dbc.Row([
        html.Div([
            html.H6("Select a Variable : "),
            dcc.RadioItems(options=[{'label': 'Real GDP', 'value': 'RGDP'}, 
                                {'label': 'Nominal GDP', 'value': 'GDP'}, 
                                {'label': 'Unemployment', 'value': 'UNEMP'}], 
                                value='RGDP', id='nc-variable', 
                    inline=True, inputStyle={"margin-right": "15px", "margin-left": "30px"})
        ], id = "select-var-block")
    ]),
    html.Hr(),
    # Add a navbar with 2 tabs
    dcc.Tabs(
        id="tabs-with-classes",
        # value='tab-2',
        parent_className='custom-tabs',
        className='custom-tabs-container',
        children=[
        dcc.Tab(label='Nowcast Current Quarter', children=[
            # dash_table.DataTable(data=nowcast.to_dict('records'), page_size=10),
            html.Hr(),
            html.H5("Nowcast for Current Quarter"),
            html.Hr(),
            dbc.Row([
                dcc.Graph(figure = {}, id='nowcast-qx')
            ]),
            html.Hr(),
            html.H5("News Releases"),
            html.Hr(),
            dbc.Row([
                # # make a select input for the vinage of the nowcast
                # dcc.Dropdown(options=nowcast_dates, value = list(nowcast.date)[-1], id='nc-date', 
                #             style={"margin-bottom": "10px"}),
                dcc.RadioItems(options=nowcast_dates, value = all_nowcast_dates[-1], id='nc-date', 
                               inline=True, inputStyle={"margin-right": "5px", "margin-left": "20px"}, 
                               style={"margin-bottom": "10px"}),
                dash_table.DataTable(data = None, page_size=50, id='nowcast-qx-news', 
                                    style_table={'overflowX': 'scroll'},
                                    style_header={
                                        'backgroundColor': 'rgb(30, 30, 30)',
                                        'border': "0px",
                                        'fontWeight': 'bold'
                                    },
                                    style_cell={
                                        'backgroundColor': '#111111',
                                        'border': "0px",
                                        'color': 'white',
                                        'padding-right': '20px'
                                    }
                )
            ]),
            html.Br()
        ]),
        dcc.Tab(label='All Nowcasts', children=[
                html.Hr(),
                html.H5("All Nowcasts and News Releases"),
                html.Hr(),
                # TODO: replace with Date selector
                dcc.RangeSlider(
                    min=0,
                    max=len(all_nowcast_dates)-1,
                    step=None,
                    marks= dict(zip(range(len(all_nowcast_dates)), 
                                pd.to_datetime(nowcast.date).dt.strftime("%b-%d %Y"))) #,
                    # value=[all_nowcast_dates[0], all_nowcast_dates[-1]]
                ),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure = {}, id='all-nowcasts-ts')
                    ], width=6),
                    dbc.Col([
                        dcc.Graph(figure = {}, id='all-nowcasts-news')
                    ], width=6),
                ])
        ]),
        dcc.Tab(label='About the Nowcast', children=[
            html.Hr(),
            html.H5("About the Nowcast"),
            html.P("The South African Nowcast is a project by Stellenbosch University's Department of Economics. The project aims to provide a timely and accurate estimate of the current state of the South African economy. The Nowcast is updated on a monthly basis, and is released on the first business day of the month."),
            html.P("The Nowcast is based on a dynamic factor model, which is estimated using a large number of economic indicators. The model is estimated using the Kalman filter, which allows for the inclusion of new data as it becomes available. The Nowcast is therefore updated on a monthly basis, and is released on the first business day of the month."),        
        ]),
    ])
], style={'max-width': '90%', 'margin': 'auto'})

@callback(
    Output('nowcast-qx', 'figure'),
    Output('nowcast-qx-news', 'data'),
    Input('nc-variable', 'value'),
    Input('nc-date', 'value')
)
def update_nccq_graphs(var, date):
    ## Nowcast for latest quarter
    news_qx = news.loc[(news.quarter == q) & (news["impacted variable"] == var)]
    news_latest_quarter = news_qx.groupby(["date", "sector_topic"]).agg({"impact": "sum"}).reset_index()
    # news_latest_quarter.impact = news_latest_quarter.impact / 10
    fig_qx = px.bar(news_latest_quarter, x="date", y="impact", color="sector_topic")
    fig_qx.add_trace(go.Scatter(x=nowcast_latest_quarter.date, y=nowcast_latest_quarter[var], 
                                line=dict(color="white"), mode='lines+markers', name='Nowcast'))
    # Edit the layout
    fig_qx.update_layout(title='Nowcast for ' + q,  barmode='stack',    
                        xaxis_title='Date', yaxis_title='Quarterly Log-Differnece Growth Rate (%)',
                        legend_title = "Sector: Topic",
                        hovermode="x", autosize=False, width=1000, height=500,
                        margin=dict(l=20, r=20, t=40, b=20), template="plotly_dark")
    # delete the hover template
    fig_qx.update_yaxes(hoverformat=".2f")
    fig_qx.update_traces(hovertemplate=None)

    news_latest_quarter_dict = news_qx[["series", "label", "observed", "forecast (prev)", # "date", "update date",
                                        "news", "weight", "impact", "broad_sector", "topic"]]
    news_latest_quarter_dict[["observed", "forecast (prev)", "news", "weight", "impact"]] = news_latest_quarter_dict[["observed", "forecast (prev)", "news", "weight", "impact"]].transform(lambda x: x.round(3))
    news_latest_quarter_dict = news_latest_quarter_dict.loc[news_qx.date == date]
    news_latest_quarter_dict = news_latest_quarter_dict.to_dict('records')
    return fig_qx, news_latest_quarter_dict


@callback(
    Output('all-nowcasts-ts', 'figure'),
    Output('all-nowcasts-news', 'figure'),
    Input('nc-variable', 'value')
)
def update_allnc_graphs(var):
    ## Time series plot of all nowcasts
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=nowcast_final.quarter, y=nowcast_final[var], 
                            customdata=nowcast_final.date, 
                            hovertemplate="%{y:.2f} (%{customdata})",
                            mode='lines+markers', name='Latest Nowcast'))
    fig.add_trace(go.Scatter(x=nowcast_other.quarter, y=nowcast_other[var], 
                            customdata=nowcast_other.date, 
                            hovertemplate="%{y:.2f} (%{customdata})",
                            mode='markers', name='Nowcast'))
    # choose last day of quarter as timestamp
    fig.add_trace(go.Scatter(x=gdp_ld.quarter, y=gdp_ld[var], hovertemplate="%{y:.2f}",
                             mode='lines+markers', name='Real GDP Growth')) # gdp_ld.index.to_timestamp(how = "end")
    # Edit the layout
    fig.update_layout(title='All Nowcasts (+ Backtesting 2019Q2-2023Q1)', 
                      xaxis_title='Quarter', 
                      yaxis_title='Quarterly Log-Differnece Growth Rate (%)', 
                      hovermode="x", 
                      autosize=False, width=750, height=500, margin=dict(l=20, r=20, t=40, b=20), 
                      template="plotly_dark")

    ## Barcharts of average news impacts
    tot_news_fig = go.Figure()
    news_tot_var = news_tot.loc[news_tot["impacted variable"] == var]
    tot_news_fig.add_bar(x=news_tot_var.sector_topic, y=news_tot_var.abs_impact)
    tot_news_fig.update_layout(title='Average Absolute News Impact',      
                    xaxis_title='Date', yaxis_title='Average Absolute Impact',
                    barmode='stack', hovermode="x", autosize=False, width=750, height=500,
                    margin=dict(l=20, r=20, t=40, b=20), template="plotly_dark")
    return fig, tot_news_fig


if __name__ == '__main__':
    app.run_server(debug=True)
# 

# %%
