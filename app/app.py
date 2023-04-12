# %% 
# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import plotly.express as px
import plotly.graph_objects as go

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
app = Dash(__name__)


app.layout = html.Div([
    # html.Div(children='My First App with Data'),
    html.H1("South Africa Nowcast"),
    # dash_table.DataTable(data=nowcast.to_dict('records'), page_size=10),
    html.Hr(),
    dcc.RadioItems(options=['RGDP', 'GDP', 'UNEMP'], value='RGDP', id='nc-variable'),
    html.Div(children='All Nowcasts'),
    dcc.Graph(figure = {}, id='nowcast-qx'),
    dash_table.DataTable(data = None, page_size=10, id='nowcast-qx-news'),
    dcc.Graph(figure = {}, id='all-nowcasts-ts'),
    dcc.Graph(figure = {}, id='all-nowcasts-news')
    # px.line(x=nowcast.index, y=nowcast.RGDP, title="Nowcast of Real GDP", 
    #    labels = dict(x ="Quarter", y ="RGDP Logdiff")).update_traces(hovertemplate=None).update_layout(hovermode="x")
])

@app.callback(
    Output('all-nowcasts-ts', 'figure'),
    Output('all-nowcasts-news', 'figure'),
    Output('nowcast-qx', 'figure'),
    Output('nowcast-qx-news', 'data'),
    Input('nc-variable', 'value')
)
def update_graphs(var):
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
    fig.update_layout(title='Nowcasts of Real GDP Growth', xaxis_title='Quarter', yaxis_title='Log-Differnece Growth Rate (%)')
    # change the hovermode to compare data points
    fig.update_layout(hovermode="x")
    # make tight layout
    fig.update_layout(autosize=False, width=750, height=500, margin=dict(l=20, r=20, t=40, b=20))

    ## Barcharts of average news impacts
    tot_news_fig = go.Figure()
    news_tot_var = news_tot.loc[news_tot["impacted variable"] == var]
    tot_news_fig.add_bar(x=news_tot_var.sector_topic, y=news_tot_var.abs_impact)
    tot_news_fig.update_layout(title='Average Absolute News Impact on Real GDP',      
                    xaxis_title='Date', yaxis_title='Average Absolute Impact',
                    barmode='stack', hovermode="x", autosize=False, width=750, height=500,
                    margin=dict(l=20, r=20, t=40, b=20))

    ## Nowcast for latest quarter
    q = nowcast.quarter.max()
    nowcast_latest_quarter = nowcast.loc[nowcast.quarter == q]
    news_latest_quarter = news.loc[(news.quarter == q) & (news["impacted variable"] == var)] \
        .groupby(["date", "sector_topic"]).agg({"impact": "sum"}).reset_index()
    # news_latest_quarter.impact = news_latest_quarter.impact / 10
    fig_qx = px.bar(news_latest_quarter, x="date", y="impact", color="sector_topic")
    fig_qx.add_trace(go.Scatter(x=nowcast_latest_quarter.date, y=nowcast_latest_quarter[var], 
                                line=dict(color="black"), mode='lines+markers', name='Nowcast'))
    # Edit the layout
    fig_qx.update_layout(title='Nowcast for ' + q,  barmode='stack',    
                        xaxis_title='Date', yaxis_title='Impact',
                        hovermode="x", autosize=False, width=750, height=500,
                        margin=dict(l=20, r=20, t=40, b=20))
    # delete the hover template
    fig_qx.update_yaxes(hoverformat=".2f")
    fig_qx.update_traces(hovertemplate=None)

    news_latest_quarter_dict = news_latest_quarter.to_dict('records')
    return fig, tot_news_fig, fig_qx, news_latest_quarter_dict


if __name__ == '__main__':
    app.run_server(debug=True)
# 

# %%
