import traceback
import asyncio
from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_plotly, render_widget
import duckdb as ddb
from preprocess import fifa_data
from os.path import dirname, abspath, join
import faicons as fa
from pathlib import Path
from chatlas import ChatOllama, content_image_url
import prompt_process
import plotly.express as px
import plotly.graph_objects as go
from explain_plot import explain_plot

project_root = dirname(abspath(__file__))
here = Path(__file__).parent

icon_explain = ui.img(src="stars.svg")
reset_icon = ui.img(src="reset.svg")

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_action_button("shot", "Takse Screenshot"),
        ui.card(
            ui.card_header("Chat Agent",ui.span(ui.input_action_link("reset_chat", reset_icon, style="color: inherit;",aria_label = "Reset Chat")),class_="d-flex justify-content-between align-items-center"),
            ui.chat_ui(
                "chat", height = "100%" 
        ),
        ),

        width = 500,
        style = "height : 100%",
        gap = "3px"
    ),
    ui.head_content(
        ui.tags.script(src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"),
        ui.tags.script(src = 'screenshot.js')
    ),
    ui.tags.link(rel = "stylesheet", href="styles.css"),
    #
    #
    #
    ui.output_text("show_title", container = ui.h3),
    ui.output_code("show_query", placeholder=False).add_style("max-height:100px; overflow:auto;"),
    #
    #
    #
    ui.layout_columns(
        ui.value_box(
            "Total Players",
            ui.output_text("total_players"),
            showcase=fa.icon_svg("user", "regular")
        ),
        ui.value_box(
            "Total Male Players",
            ui.output_text("total_male_players"),
            showcase=fa.icon_svg("user", "regular")
        ),
        ui.value_box(
            "Total Female Players",
            ui.output_text("total_female_players"),
            showcase=fa.icon_svg("user", "regular")
        ),

        fill=False
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Player Data"),
            ui.output_data_frame("table"),
            full_screen=True
        ),
    ui.card(
        ui.card_header("Pace and Dribble Analysis", 
        ui.span(ui.input_action_link("interpret_pace_vs_dribble", icon_explain, class_ = "me-3", aria_label = "Explain the bar graph")),
        class_="d-flex justify-content-between align-items-center",
        ),
        output_widget("pac_vs_dribble"),
        full_screen=True
    ),
    ),
    ui.card("The image Agent sees" , ui.output_ui("preview_img")), #remove
    title="Fifa 26 player data",
    fillable = True,

)


def server(input, output, session):

    current_query = reactive.Value("")
    current_title = reactive.Value("")
    current_image = reactive.Value("") #remove
    screenshot_future = None

    @reactive.effect
    @reactive.event(input.shot)
    async def _():
        await session.send_custom_message("take_screenshot", {})

    @reactive.calc
    def fifa_filter():
        if current_query() == "":
            return fifa_data
        return ddb.query(current_query()).df()
    
    @render.text
    def total_players():
        data = fifa_filter()
        if data.empty:
            return "0"
        return str(len(data))

    @render.text
    def total_male_players():
        data = fifa_filter()
        if data.empty:
            return "0"
        return str(len(data.loc[data['GENDER'] == 'M']))

    @render.text
    def total_female_players():
        data = fifa_filter()
        if data.empty:
            return "0"
        return str(len(data.loc[data['GENDER'] == 'F']))
    
    
    @render.text
    def show_title():
        return current_title()
    
    @render.text
    def show_query():
        return current_query()

    @render.data_frame
    def table():
        return render.DataGrid(fifa_filter())
    
    @render_plotly
    def pac_vs_dribble():
        data = fifa_filter()
        if ("PAC" in data.columns) and ("DRI" in data.columns):
            fig = px.scatter(data, x="PAC", y="DRI")
            return fig
    
    @render.ui
    def preview_img():
        if input.screenshot_data() is None:
            return 
        current_image.set(input.screenshot_data())
        return ui.img(src=current_image())

    

    #================================================================
    #chat bot configuration
    Chat = ChatOllama
    chat_model = "ministral-3:8b"
    chat_session = Chat(system_prompt=prompt_process.system_prompt(fifa_data, "fifa"), model = chat_model)
    print(chat_session.system_prompt)

    async def update_filter(query, title):
        async with reactive.lock():
            current_query.set(query)
            current_title.set(title)
            await reactive.flush()
    
    async def query_db(query: str):
        """Perform a SQL query on the data, and return the results as JSON.

        Args:
            query: A DuckDB SQL query; must be a SELECT statement.
        """
        print(ddb.query(query).to_df().to_json(orient="records"))
        return ddb.query(query).to_df().to_json(orient="records")
    
    async def update_dashboard(query: str, title: str):
        """Modifies the data presented in the data dashboard, based on the given SQL query,
        and also updates the title.

        Args:
            query: A DuckDB SQL query; must be a SELECT statement, or an empty string to reset the dashboard.
            title: A title to display at the top of the data dashboard, summarizing the intent of the SQL query.
        """
        if query != "":
            await query_db(query)
        await update_filter(query, title)

    @reactive.effect
    @reactive.event(input.screenshot_data)
    async def capture_screenshot_data():
        nonlocal screenshot_future
        # If we are waiting for a screenshot, resolve the future with the new data
        if screenshot_future and not screenshot_future.done():
            data = input.screenshot_data()
            if data:
                screenshot_future.set_result(data)

    async def take_screenshot():
        print("agent has called the tool")
        """use this tool to take the screen shot of the dashboard in which you are working on. this tool gives you the screenshot. you can use this to gather information on what is happening in the dashboard."""
        nonlocal screenshot_future
        
        # Create a new future for this request
        screenshot_future = asyncio.Future()
        
        # Trigger the client action
        await session.send_custom_message("take_screenshot", {})
        
        try:
            # Wait for the effect above to resolve this future (timeout after 10s to be safe)
            image_data = await asyncio.wait_for(screenshot_future, timeout=10.0)
            current_image.set(image_data)
            return content_image_url(image_data)
        except asyncio.TimeoutError:
            return "Error: Screenshot timed out."
    


    def fork_session():
        """
        ok, this is used to for or snapshot current chat session into a newone.
        this is useful to make a new chat session that is a copy of the current one. this is very useful when we pass or use the explain graph scenario.
        """

        new_session = Chat(system_prompt=prompt_process.system_prompt(fifa_data, "fifa"), model = chat_model)
        new_session.register_tool(update_dashboard)
        new_session.register_tool(query_db)
        new_session.register_tool(take_screenshot)
        new_session.set_turns(chat_session.get_turns()) #copy the main chat data to the explanation agent
        return new_session
    
    chat_session.register_tool(update_dashboard)
    chat_session.register_tool(query_db)
    chat_session.register_tool(take_screenshot)

    def reset_chat_session():
        nonlocal chat_session
        chat_session.set_turns([])
        chat_session = Chat(
            system_prompt=prompt_process.system_prompt(fifa_data, "fifa"),
            model=chat_model
        )
        chat_session.register_tool(update_dashboard)
        chat_session.register_tool(query_db)
        chat_session.register_tool(take_screenshot)

    #===============================================================================

    chat = ui.Chat("chat", messages=["Hello this is your dashboard agent"])

    @chat.on_user_submit
    async def perform_chat(user_input: str):
        try:
            stream = await chat_session.stream_async(user_input, echo="all")
        except Exception as e:
            traceback.print_exc()
            return await chat.append_message(f"**Error** : {e}")
        await chat.append_message_stream(stream)
    
    @reactive.effect
    @reactive.event(input.reset_chat)
    async def reset_chat():
        reset_chat_session()

        current_query.set("")
        current_title.set("")

        await chat.clear_messages()
        await chat.append_message("Hello this is your dashboard agent")
    #===================================================================================
    #Interpretting codes

    @reactive.effect
    @reactive.event(input.interpret_pace_vs_dribble)
    async def interpret_pace_vs_dribble():
        await explain_plot(fork_session(), go.FigureWidget(pac_vs_dribble.widget))






app = App(app_ui, server, static_assets=here / "www")

