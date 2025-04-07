import dash
import pandas as pd
import numpy as np
import psycopg2
from sqlalchemy import create_engine
from dash import dcc, html, dash_table
import dash_daq as daq
import datetime
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import io

# PostgreSQL database connection string using SQLAlchemy
db_url = "postgresql://bumeharaz:22dgx1hJ7YD7i5JLxdCgePaGGgpjSIEI@dpg-cvpnc7pr0fns7384f250-a.oregon-postgres.render.com/dbname_8ftz"

# Create engine for SQLAlchemy
engine = create_engine(db_url)

# Function to fetch data from PostgreSQL database
def fetch_data(query):
    try:
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# Fetching data for initial and auto-refresh
def get_initial_data():
    query = """
    SELECT total_registered, visitors, applied_to_job, application, unique_applicant,
            total_companies_jobs_apply, direct_payment_for_job_apply, paid_by_applicants,
            became_pro_user_today, amount_from_today_pro_users, pro_job_seeker_count, total_amount_collected
    FROM public.fair_summary_data
    LIMIT 1;
    """
    return fetch_data(query)

def get_hourly_data():
    query = """
    SELECT intervalstart, opidcount FROM public.opidintervalcounts ORDER BY intervalstart;
    """
    return fetch_data(query)

def get_transaction_data():
    query = """
    SELECT hour, amount FROM Transactions ORDER BY hour;
    """
    return fetch_data(query)

# Preparing hourly data
def prepare_hourly_data(df):
    df['intervalstart'] = pd.to_datetime(df['intervalstart'])
    df['Hour'] = df['intervalstart'].dt.hour
    hourly_data = df.groupby('Hour')['opidcount'].sum().reset_index()
    return hourly_data

# Preparing the initial data for column-wise display
def prepare_column_data(df):
    column_mapping = {
        'total_registered': 'Total Registered',
        'visitors': 'Visitors',
        'applied_to_job': 'Applied to Job',
        'application': 'Applications',
        'unique_applicant': 'Unique Applicants',
        'total_companies_jobs_apply': 'Total Companies Jobs Applied',
        'direct_payment_for_job_apply': 'Direct Payment for Job Apply',
        'paid_by_applicants': 'Paid by Applicants',
        'became_pro_user_today': 'Became Pro User Today',
        'amount_from_today_pro_users': 'Amount from Today Pro Users',
        'pro_job_seeker_count': 'Pro Job Seeker Count',
        'total_amount_collected': 'Total Amount Collected'
    }

    columns_to_show = list(column_mapping.keys())
    last_row = df[columns_to_show].iloc[[-1]]

    column_wise_data = [{'Attribute': column_mapping[col], 'Value': last_row[col].values[0]} for col in last_row.columns]
    return column_wise_data

# Preparing the initial data for percentage display
def prepare_percentage_data(df):
    total_registered = df['total_registered'].iloc[0]
    visitors = df['visitors'].iloc[0]
    direct_payment = df['direct_payment_for_job_apply'].iloc[0]
    total_payment = df['total_amount_collected'].iloc[0]
    paid_applicants = df['paid_by_applicants'].iloc[0]
    pro_users = df['became_pro_user_today'].iloc[0]
    pro_amount = df['amount_from_today_pro_users'].iloc[0]

    percentage_data = [
        {'Attribute': 'Visitors vs Total Registered', 'Percentage (%)': round((visitors / total_registered) * 100, 2) if total_registered else 0},
        {'Attribute': 'Direct Payment vs Total Payment', 'Percentage (%)': round((direct_payment / total_payment) * 100, 2) if total_payment else 0},
        {'Attribute': 'Paid Applicants vs Visitors', 'Percentage (%)': round((paid_applicants / visitors) * 100, 2) if visitors else 0},
        {'Attribute': 'Pro Users vs Visitors', 'Percentage (%)': round((pro_users / visitors) * 100, 2) if visitors else 0},
        {'Attribute': 'Pro Amount vs Total Amount', 'Percentage (%)': round((pro_amount / total_payment) * 100, 2) if total_payment else 0}
    ]
    return percentage_data


# Initialize Dash app
app = dash.Dash(__name__)


# Light & Dark Themes with Enhanced Glassmorphism Effect
LIGHT_THEME = {
    'background': 'linear-gradient(to bottom, #f7f7f7, #ddd)',
    'textColor': '#333',
    'tabColor': 'rgba(255, 255, 255, 0.7)',
    'footerBg': 'rgba(255, 255, 255, 0.6)',
    'glassEffect': 'rgba(255, 255, 255, 0.3)',
    'shadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
    'tabTextColor': '#000000',
    'socialIconColor': '#000000',
    'countdownTextColor': '#000',
    'countdownShadowColor': 'rgba(0, 0, 0, 0.5)',
}

DARK_THEME = {
    'background': 'linear-gradient(to bottom, #1E1E1E, #2C3E50)',
    'textColor': '#ECF0F1',
    'tabColor': 'rgba(0, 0, 0, 0.7)',
    'footerBg': 'rgba(0, 0, 0, 0.6)',
    'glassEffect': 'rgba(0, 0, 0, 0.3)',
    'shadow': '0 4px 30px rgba(255, 255, 255, 0.1)',
    'tabTextColor': '#FFFFFF',
    'socialIconColor': '#FFFFFF',
    'countdownTextColor': '#fff',
    'countdownShadowColor': 'rgba(255, 255, 255, 0.5)',
}

# Layout
app.layout = html.Div(id='main-container', style={
    'display': 'flex',
    'flexDirection': 'column',
    'minHeight': '100vh',
    'background': 'linear-gradient(135deg, #1e1e1e, #2c3e50)',
    'background-size': '200% 200%',
    'animation': 'gradientAnimation 15s ease infinite',
}, children=[
    dcc.Store(id='theme-store', storage_type='local', data={'theme': 'dark'}),
    dcc.Store(id='timer-trigger', data=1),  # Trigger to start the timer

    html.Div(style={
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'space-between',
        'padding': '10px 20px',
        'backdropFilter': 'blur(10px)',
        'backgroundColor': 'rgba(255, 255, 255, 0.3)',
        'borderRadius': '15px',
        'boxShadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
        'margin': '10px',
    }, children=[
        html.Img(
            src='https://www.bdjobs.com/jobfair/new_reg/images/bdjobs-chakri-mela.svg',
            style={
                'height': 'auto',
                'maxWidth': '120px',
                'filter': 'drop-shadow(2px 2px 4px rgba(0, 0, 0, 0.3))',
                'animation': 'pulse 2s infinite ease-in-out',
            }
        ),
        html.H1('Technical Job Fair', id='title-text', style={
            'textAlign': 'center',
            'flex': '1',
            'fontSize': 'clamp(18px, 3vw, 32px)',
            'textShadow': '2px 2px 4px rgba(0, 0, 0, 0.3)',
            'color': '#333',
        }),
        daq.ToggleSwitch(id='theme-toggle', value=True, label="Dark Mode", labelPosition="bottom")
    ]),

    # Countdown Section
    html.Div(
        id='countdown-container',
        style={'textAlign': 'center', 'margin': '20px 0'},
        children=[
            html.Div(
                id='countdown-timer',
                style={
                    'fontSize': '24px',
                    'fontWeight': 'bold',
                    'textShadow': '2px 2px 4px rgba(0, 0, 0, 0.5)',
                    'color': 'inherit',
                },
            ),
            html.Div(
                id='fair-time-countdown',
                style={
                    'fontSize': '16px',
                    'color': 'inherit',
                    'textShadow': '1px 1px 2px rgba(0,0,0,0.3)',
                },
            ),
        ],
    ),

    dcc.Tabs(
        id="tabs",
        value='summary',
        children=[
            dcc.Tab(label='📊 Summary', value='summary', id="summary-tab", style={
                'backgroundColor': 'rgba(255, 255, 255, 0.7)',
                'borderRadius': '10px',
                'margin': '5px',
                'boxShadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
                'color': '#000000',
                'transition': 'background-color 0.3s ease, box-shadow 0.3s ease',
            }),
            dcc.Tab(label='👥 Applicants', value='pie-charts', id="applicants-tab", style={
                'backgroundColor': 'rgba(255, 255, 255, 0.7)',
                'borderRadius': '10px',
                'margin': '5px',
                'boxShadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
                'color': '#000000',
                'transition': 'background-color 0.3s ease, box-shadow 0.3s ease',
            }),
            dcc.Tab(label='৳ Transactions', value='transaction', id="transaction-tab", style={
                'backgroundColor': 'rgba(255, 255, 255, 0.7)',
                'borderRadius': '10px',
                'margin': '5px',
                'boxShadow': '0 4px 30px rgba(0, 0, 0, 0.1)',
                'color': '#000000',
                'transition': 'background-color 0.3s ease, box-shadow 0.3s ease',
            })
        ],
        style={'marginBottom': '20px'}
    ),
    
     html.Div(id='tabs-content', style={'flex': '1', 'transition': 'opacity 0.5s ease'}),

    # dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),
     dcc.Interval(id='refresh-trigger', interval=60000, n_intervals=0),  # Change interval to 60 seconds

    html.Div(id='download-data', style={'display': 'none'}),
    dcc.Download(id="download-excel"),
    html.Footer(id='footer', children=[
        html.P("© 2025 Meharaz Hossain", id='footer-text', style={'textAlign': 'center', 'fontSize': '14px'}),
        html.P("Contact: meharazhossaindiu@gmail.com", style={'textAlign': 'center', 'fontSize': '14px'}),

        html.Div(id='social-icons', children=[
            html.A(html.Img(
                src="https://img.icons8.com/ios-filled/50/000000/facebook.png",
                style={
                    'width': '35px', 'height': '35px', 'borderRadius': '50%',
                    'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                    'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                    'filter': 'brightness(1.2)',
                }
            ), href="https://facebook.com", target="_blank", style={'margin': '0 10px'}),
            html.A(html.Img(
                src="https://img.icons8.com/ios-filled/50/00000000/twitter.png",
                style={
                    'width': '35px', 'height': '35px', 'borderRadius': '50%',
                    'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                    'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                    'filter': 'brightness(1.2)',
                }
            ), href="https://twitter.com", target="_blank", style={'margin': '0 10px'}),

            html.A(html.Img(
                src="https://img.icons8.com/ios-filled/50/000000/linkedin.png",
                style={
                    'width': '35px', 'height': '35px', 'borderRadius': '50%',
                    'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                    'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                    'filter': 'brightness(1.2)',
                }
            ), href="https://www.linkedin.com/in/meharaz-hossain-aa1434245/", target="_blank", style={'margin': '0 10px'})
        ], style={'display': 'flex', 'justifyContent': 'center', 'gap': '15px', 'marginTop': '10px'})
    ], style={
        'position': 'sticky',
        'bottom': '0',
        'width': '100%',
        'marginTop': 'auto',
        'backdropFilter': 'blur(10px)',
        'backgroundColor': 'rgba(189, 195, 199, 0.6)',
        'padding': '15px 0',
        'textAlign': 'center',
        'borderRadius': '15px 15px 0 0',
        'boxShadow': '0 -4px 30px rgba(0, 0, 0, 0.1)',
        'transition': 'background-color 0.3s ease',
    })
])


# Load the theme from storage when the page is refreshed
@app.callback(
    [Output('main-container', 'style'),
     Output('title-text', 'style'),
     Output('summary-tab', 'style'),
     Output('applicants-tab', 'style'),
     Output('transaction-tab', 'style'),
     Output('footer', 'style'),
     Output('footer-text', 'style'),
     Output('social-icons', 'children'),
     Output('countdown-container', 'style'),
     Output('countdown-timer', 'style'),
     Output('fair-time-countdown', 'style'),
     Output('tabs-content', 'style'),
     ],
    Input('theme-store', 'data'),
    Input('timer-trigger', 'data')  # Add timer trigger as input
)
def load_theme(stored_data, timer_trigger):
    theme_name = stored_data['theme'] if stored_data else 'dark'
    is_dark_mode = theme_name == 'dark'
    theme = DARK_THEME if is_dark_mode else LIGHT_THEME

    social_icons = [
        html.A(html.Img(
            src=f"https://img.icons8.com/ios-filled/50/{theme['socialIconColor'].lstrip('#')}/facebook.png",
            style={
                'width': '35px', 'height': '35px', 'borderRadius': '50%',
                'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                'filter': 'brightness(1.2)',
            }
        ), href="https://facebook.com", target="_blank", style={'margin': '0 10px'}),

        html.A(html.Img(
            src=f"https://img.icons8.com/ios-filled/50/{theme['socialIconColor'].lstrip('#')}/twitter.png",
            style={
                'width': '35px', 'height': '35px', 'borderRadius': '50%',
                'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                'filter': 'brightness(1.2)',
            }
        ), href="https://twitter.com", target="_blank", style={'margin': '0 10px'}),

        html.A(html.Img(
            src=f"https://img.icons8.com/ios-filled/50/{theme['socialIconColor'].lstrip('#')}/linkedin.png",
            style={
                'width': '35px', 'height': '35px', 'borderRadius': '50%',
                'opacity': '0.9', 'boxShadow': '0px 4px 10px rgba(0, 0, 0, 0.4)',
                'transition': 'transform 0.3s ease, box-shadow 0.3s ease, color 0.3s ease',
                'filter': 'brightness(1.2)',
            }
        ), href="https://www.linkedin.com/in/meharaz-hossain-aa1434245/", target="_blank", style={'margin': '0 10px'})
    ]

    return [
        {'display': 'flex', 'flexDirection': 'column',
         'minHeight': '100vh', 'background': theme['background'], 'color': theme['textColor'], 'background-size': '200% 200%', 'animation': 'gradientAnimation 15s ease infinite'},
        {'color': theme['textColor']},
        {'backgroundColor': theme['tabColor'], 'color': theme['tabTextColor'], 'borderRadius': '10px',
         'boxShadow': theme['shadow'], 'transition': 'background-color 0.3s ease, box-shadow 0.3s ease'},
        {'backgroundColor': theme['tabColor'], 'color': theme['tabTextColor'], 'borderRadius': '10px',
         'boxShadow': theme['shadow'], 'transition': 'background-color 0.3s ease, box-shadow 0.3s ease'},
        {'backgroundColor': theme['tabColor'], 'color': theme['tabTextColor'], 'borderRadius': '10px',
         'boxShadow': theme['shadow'], 'transition': 'background-color 0.3s ease, box-shadow 0.3s ease'},
        {'backgroundColor': theme['footerBg'], 'padding': '15px 0', 'textAlign': 'center', 'backdropFilter': 'blur(10px)', 'borderRadius': '15px 15px 00 0', 'boxShadow': theme['shadow'], 'transition': 'background-color 0.3s ease'},
        {'color': theme['textColor']},
        social_icons,
        {'textAlign': 'center', 'margin': '20px 0', 'color': theme['countdownTextColor']},
        {
            'fontSize': '24px',
            'fontWeight': 'bold',
            'textShadow': f'2px 2px 4px {theme["countdownShadowColor"]}',
            'color': theme['countdownTextColor'],
            'transition': 'color 0.5s ease'
        },
        {
            'fontSize': '16px',
            'color': theme['countdownTextColor'],
            'textShadow': f'1px 1px 2px {theme["countdownShadowColor"]}',
            'transition': 'color 0.5s ease'
        },
        {'flex': '1', 'transition': 'opacity 0.5s ease'},
    ]

# Update the theme when the toggle button is clicked
@app.callback(
    Output('theme-store', 'data'),
    Input('theme-toggle', 'value'),
    State('theme-store', 'data'),
    prevent_initial_call=True
)
def toggle_theme(is_dark_mode, stored_data):
    if stored_data is None:
        stored_data = {'theme': 'dark'}

    new_theme = 'dark' if is_dark_mode else 'light'
    stored_data['theme'] = new_theme
    return stored_data

# Set the initial state of the toggle switch based on the stored theme
@app.callback(
    Output('theme-toggle', 'value'),
    Input('theme-store', 'data')
)
def set_toggle_initial_state(stored_data):
    if stored_data and 'theme' in stored_data:
        return stored_data['theme'] == 'dark'
    return True

# Clientside Callback for Timer (No Refresh Required)
app.clientside_callback(
    """
    function(trigger) {
        function updateTimer() {
            try {
                const eventTime = new Date(2025, 3, 23, 9, 0, 0);
                const eventEndTime = new Date(2025, 3, 23, 16, 0, 0);
                const now = new Date();
                let countdownText = "";
                let fairTimeText = "";

                if (now < eventTime) {
                    let timeLeft = eventTime - now;
                    let days = Math.floor(timeLeft / (1000 * 60 * 60 * 24));
                    let hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    let minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
                    let seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
                    countdownText = `Event Starts In: ${days} days, ${hours.toString().padStart(2, '0')} hours, ${minutes.toString().padStart(2, '0')} minutes, ${seconds.toString().padStart(2, '0')} seconds`;
                    fairTimeText = "";
                } else if (now >= eventTime && now <= eventEndTime) {
                    let timeLeft = eventEndTime - now;
                    let hours = Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    let minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
                    let seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);
                    countdownText = "Event Started!";
                    fairTimeText = `Event Ends In: ${hours.toString().padStart(2, '0')} hours, ${minutes.toString().padStart(2, '0')} minutes, ${seconds.toString().padStart(2, '0')} seconds`;
                } else {
                    countdownText = "Event Ended!";
                    fairTimeText = "";
                }

                document.getElementById("countdown-timer").innerText = countdownText;
                document.getElementById("fair-time-countdown").innerText = fairTimeText;
            } catch (error) {
                console.error("Error updating timer:", error);
            }
        }

        setInterval(updateTimer, 1000);
        updateTimer();  // Call immediately to update UI instantly

        return window.dash_clientside.no_update;
    }
    """,
    Output("timer-trigger", "data"),
    Input("timer-trigger", "data")
)

# Add CSS animations
app.clientside_callback(
    """
    function(dummy) {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.05); }
                100% { transform: scale(1); }
            }
            .dash-tab:hover {
                background-color: rgba(200, 200, 200, 0.7);
                box-shadow: 0 6px 35px rgba(0, 0, 0, 0.2);
            }
            #social-icons a img:hover {
                transform: scale(1.1);
                box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.5);
            }
            @keyframes gradientAnimation {
                0% { background-position: 91% 0%; }
                50% { background-position: 10% 100%; }
                100% { background-position: 91% 0%; }
            }
            .dash-tab-content {
                animation: slideIn 0.5s ease-out;
            }
            @keyframes slideIn {
                from {
                    transform: translateY(20px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }
            #countdown-timer{
                transform-style: preserve-3d;
            }
            #countdown-timer > div{
                transform: rotateX(0deg);
                transition: transform 0.5s ease;
            }
            #countdown-timer.flip > div{
                transform: rotateX(180deg);
            }
        `;
        document.head.appendChild(style);
        return null;
    }
    """,
    Output('main-container', 'data-dummy'),
    Input('main-container', 'id'),
)

#Flip animation trigger.
app.clientside_callback(
    """
    function(current, previous) {
        if (current!== previous && previous!== undefined) {
            const countdownTimer = document.getElementById("countdown-timer");
            countdownTimer.classList.add("flip");
            setTimeout(() => {
                countdownTimer.classList.remove("flip");
            }, 500);
        }
        return current;
    }
    """,
    Output("countdown-timer","data-trigger"),
    Input("countdown-timer","children"),
    State("countdown-timer","data-trigger")
)

@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs', 'value'),
    Input('refresh-trigger', 'n_intervals')
)
def render_content(tab, n):
    if tab == 'summary':
        df = get_initial_data()
        column_data = prepare_column_data(df)
        percentage_data = prepare_percentage_data(df)

        return html.Div([
            dcc.Loading(
                id="loading-table",
                type="circle",
                children=[
                    html.Div(style={'display': 'flex', 'justifyContent': 'space-around'}, children=[
                        html.Div([
                            #html.H3("Summary Data", style={'textAlign': 'center', 'color': '#4CAF50'}),
                            dash_table.DataTable(
                                id='data-table',
                                columns=[{"name": col, "id": col} for col in ['Attribute', 'Value']],
                                data=column_data,
                                style_table={'height': 'auto', 'width': '100%',
                                             'boxShadow': '0 4px 8px 0 rgba(0, 0, 0, 0.2)'},
                                style_cell={'textAlign': 'center', 'fontSize': '16px',
                                             'backgroundColor': '#2B3B4B', 'color': 'white'},
                                style_header={'backgroundColor': '#4F5D75', 'color': 'white'}
                            )
                        ], style={'width': '45%'}),

                        html.Div([
                            #html.H3("Percentage Data", style={'textAlign': 'center', 'color': '#4CAF50'}),
                            dash_table.DataTable(
                                id='percentage-table',
                                columns=[{"name": col, "id": col} for col in ['Attribute', 'Percentage (%)']],
                                data=percentage_data,
                                style_table={'height': 'auto', 'width': '100%',
                                             'boxShadow': '0 4px 8px 0 rgba(0, 0, 0, 0.2)'},
                                style_cell={'textAlign': 'center', 'fontSize': '16px',
                                             'backgroundColor': '#2B3B4B', 'color': 'white'},
                                style_header={'backgroundColor': '#4F5D75', 'color': 'white'}
                            )
                        ], style={'width': '45%'})
                    ])
                ]
            ),
            html.Div([
                html.Button("Download Excel", id="download-button", n_clicks=0,
                            style={'background-color': '#4CAF50', 'color': 'white', 'font-size': '16px',
                                   'padding': '10px 24px', 'border': 'none', 'cursor': 'pointer',
                                   'border-radius': '5px', 'margin': '10px'})
            ], style={'textAlign': 'center', 'marginTop': '20px'})
        ])
    elif tab == 'pie-charts':
        df = get_initial_data()
        pie_chart_1, pie_chart_2, pie_chart_3 = create_pie_charts(df)
        return html.Div([
            html.Div([
                dcc.Graph(id='pie-chart-1', figure=pie_chart_1, style={'width': '33%', 'display': 'inline-block'}),
                dcc.Graph(id='pie-chart-2', figure=pie_chart_2, style={'width': '33%', 'display': 'inline-block'}),
                dcc.Graph(id='pie-chart-3', figure=pie_chart_3, style={'width': '33%', 'display': 'inline-block'}),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginTop': '20px'})
        ])
    elif tab == 'transaction':
        return html.Div([
            dcc.Interval(id='animation-interval', interval=1000, n_intervals=0, max_intervals=7, disabled=True),
            dcc.Dropdown(id='plot-type-dropdown', options=[{'label': '5-Minute Interval Data', 'value': '5min'}, {'label': 'Hourly Data', 'value': 'hourly'}], value='5min', style={'width': '50%', 'margin': '0 auto', 'padding': '10px', 'backgroundColor': '#eee0dd', 'color': 'Black'}),
            dcc.Graph(id='interval-graph', style={'height': '60vh', 'marginTop': '20px'}),
            html.H1("Hourly Transaction Data (9 AM - 4 PM)", style={'textAlign': 'center', 'color': '#4CAF50'}),
            dcc.Dropdown(id='graph-type', options=[{'label': 'Line Chart', 'value': 'line'}, {'label': 'Bar Chart', 'value': 'bar'}, {'label': 'Scatter Plot', 'value': 'scatter'}], value='line', clearable=False, style={'width': '50%', 'margin': 'auto', 'backgroundColor': '#eee0dd', 'color': 'Black'}),
            dcc.Graph(id='animated-chart'),
            html.Button("Start", id="start-button", n_clicks=0, style={'background-color': '#008CBA', 'color': 'white', 'font-size': '16px', 'padding': '10px 24px', 'border': 'none', 'cursor': 'pointer', 'border-radius': '5px', 'margin': '20px auto', 'display': 'block'})
           
        ])

def create_pie_charts(df):
    # Pie chart 1 - Total Registered vs Visitors
    pie_chart_1 = {
        'data': [
            go.Pie(
                labels=['Total Registered', 'Visitors'],
                values=[df['total_registered'].iloc[0], df['visitors'].iloc[0]],
                hole=0.3,
                marker=dict(colors=['#FFA500', '#1E90FF']),
                hoverinfo='label+value+percent'
            )
        ],
        'layout': go.Layout(
            title='Total Registered vs Visitors',
            showlegend=True,
            height=400,
        )
    }

    # Pie chart 2 - Applied to Job vs Application
    pie_chart_2 = {
        'data': [
            go.Pie(
                labels=['Apply Limit Amount', 'Pro User Amount'],
                values=[df['direct_payment_for_job_apply'].iloc[0], df['amount_from_today_pro_users'].iloc[0]],
                hole=0.3,
                marker=dict(colors=['#FFA500', '#1E90FF']),
                hoverinfo='label+value+percent'
            )
        ],
        'layout': go.Layout(
            title='Apply Limit Amount VS Pro User Amount',
            showlegend=True,
            height=400,
        )
    }

    # Pie chart 3 - Unique Applicant vs Pro Job Seeker Count
    pie_chart_3 = {
        'data': [
            go.Pie(
                labels=['Unique Applicant', 'Pro Job Seeker Count'],
                values=[df['unique_applicant'].iloc[0], df['pro_job_seeker_count'].iloc[0]],
                hole=0.3,
                marker=dict(colors=['#FFA500', '#1E90FF']),
                hoverinfo='label+value+percent'
            )
        ],
        'layout': go.Layout(
            title='Unique Applicants vs Pro Job Seeker Count',
            showlegend=True,
            height=400,
        )
    }
    return pie_chart_1, pie_chart_2, pie_chart_3

@app.callback(
    Output('interval-graph', 'figure'),
    [Input('plot-type-dropdown', 'value')]
)
def update_graph(plot_type):
    df = get_hourly_data()
    hourly_data = prepare_hourly_data(df)

    if plot_type == '5min':
        figure = go.Figure(data=[go.Scatter(
            x=df['intervalstart'],
            y=df['opidcount'],
            mode='lines+markers+text',
            name='OPID Count',
            marker=dict(color='#FF6347', size=10),
            line=dict(color='#FF6347', width=2),
            text=df['opidcount'],
            textposition='top center',
            hoverinfo='x+y+text'
        )])
        figure.update_layout(
            title='5-Minute Interval Pro Purchase in Fair Day',
            xaxis_title='Time',
            yaxis_title='OPID Count',
            plot_bgcolor='#eee0dd',
            paper_bgcolor='rgb(238, 224, 221)',
            font=dict(family='Arial, sans-serif', color='#333')
        )

    elif plot_type == 'hourly' and not hourly_data.empty:
        figure = go.Figure(data=[go.Bar(
            x=hourly_data['Hour'],
            y=hourly_data['opidcount'],
            name='OPID Count',
            marker=dict(color='#6A5ACD'),
            text=hourly_data['opidcount'],
            textposition='auto',
            hoverinfo='x+y+text'
        )])
        figure.update_layout(
            title='Hourly Pro Purchase in Fair Day',
            xaxis_title='Hour',
            yaxis_title='OPID Count',
            plot_bgcolor='#eee0dd',
            paper_bgcolor='rgb(238, 224, 221)',
            font=dict(family='Arial, sans-serif', color='#333')
        )

    else:
        figure = go.Figure()
        figure.update_layout(
            title='No Data Available',
            xaxis_title='Time',
            yaxis_title='OPID Count',
            plot_bgcolor='#eee0dd',
            paper_bgcolor='rgb(238, 224, 221)',
            font=dict(family='Arial, sans-serif', color='#333')
        )

    return figure

@app.callback(
    Output('animation-interval', 'disabled'),
    Input('start-button', 'n_clicks')
)
def start_animation(n_clicks):
    return False if n_clicks > 0 else True

@app.callback(
    Output('animated-chart', 'figure'),
    [Input('animation-interval', 'n_intervals'),
     Input('graph-type', 'value')]
)
def update_figure(n_intervals, graph_type):
    df = get_transaction_data()

    if not df.empty and 'hour' in df.columns:
        df = df.sort_values(by='hour')
        selected_hour = min(9 + n_intervals, 16)
        filtered_df = df[df["hour"] <= selected_hour]

        if graph_type == 'line':
            fig = px.line(filtered_df, x="hour", y="amount", markers=True,
                          title="Transaction Amounts Over Time", line_shape='linear',
                          color_discrete_sequence=['#FF5733'],
                          text="amount")
            fig.update_traces(mode='lines+markers+text',
                              marker=dict(size=10, line=dict(width=2, color='black')),
                              textposition='top center')
        elif graph_type == 'bar':
            fig = px.bar(filtered_df, x="hour", y="amount",
                          title="Transaction Amounts Over Time", color="amount",
                          color_continuous_scale='Bluered',
                          text="amount")
            fig.update_traces(textposition='auto')
        else:
            fig = px.scatter(filtered_df, x="hour", y="amount", size="amount",
                            title="Transaction Amounts Over Time", color="amount",
                            color_continuous_scale='Viridis',
                            text="amount")
            fig.update_traces(textposition='top center')

        fig.update_layout(
            yaxis=dict(title='Amount (Taka)', gridcolor='lightgray'),
            xaxis=dict(title='Hour', gridcolor='lightgray'),
            plot_bgcolor='#eee0dd', paper_bgcolor='#F4F6F6'
        )
        return fig
    return go.Figure()

# Callback for downloading data
@app.callback(
    Output("download-excel", "data"),
    Input("download-button", "n_clicks"),
    State("data-table", "data"),
    prevent_initial_call=True
)
def download_csv(n_clicks, table_data):
    if n_clicks > 0:
        # Convert table data to DataFrame
        df = pd.DataFrame(table_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
        output.seek(0)
        return dcc.send_bytes(output.getvalue(), filename="fair_summary_data.xlsx")
    return None

server = app.server

# Run App
if __name__ == "__main__":
    app.run_server(debug=True)
