import altair as alt
import pandas as pd
import streamlit as st
import requests
import json
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import PromptTemplate
import sqlite3

# Show the page title and description.
st.set_page_config(page_title="Music dataset", page_icon="♪")
st.title("♪ Music dataset")

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None
if "mode" not in st.session_state:
    st.session_state['mode'] = "Dashboard"
st.session_state['api_key'] = "test"
if not st.session_state.api_key:
    #with st.sidebar:
    api_key=st.text_input("Enter password to get started:", type="password")
    if api_key == "F@k3pa$$word":
        st.session_state['api_key'] =api_key
        st.rerun()

def load_data():
    db = SQLDatabase.from_uri("sqlite:///Chinook.db")
    return db

if st.session_state['api_key']:
    if st.session_state.mode == "Explore Data":
        if st.button('Go Back'):
            st.session_state.mode = 'Dashboard'
            st.rerun()
        st.write(
            """
            This app visualizes data from CHINOOK database (https://www.kaggle.com/datasets/nancyalaswad90/chinook-sample-database)
            It includes 11 tables and Over 15,000 rows of data.
            """
        )
        st.write("Click on the table name to load table data.")
        db = load_data()
        table_names = db.get_usable_table_names()
        begin = 0
        while begin < len(table_names):
            end  =  begin + 4
            if end > len(table_names):
                end = len(table_names)
            
            for text, col in zip(table_names[begin:end], st.columns(4)):
                if col.button(text):
                    con = sqlite3.connect("Chinook.db")
                    df = pd.read_sql_query("SELECT * from " + text + " ", con)
                    st.dataframe(
                    df,
                    hide_index=True, use_container_width=True)
                    con.close()
            begin = begin + 4

    else:
        if st.button('Explore Data'):
            st.session_state.mode = 'Explore Data'
            st.rerun()    
        questions = ["Find all albums for the artist 'AC/DC'.",
            "Find the total duration of all tracks grouped by genre.",
            "List all customers from Canada.",
            "Find the number of invoices grouped by customer. Also return customer's name. Combine first and last name.",
            "List top 5 tracks that are longer than 5 minutes. Also display track time.",
            "Who are the top 5 customers by total purchase?"]

        url = 'https://f4wo0au9r5.execute-api.us-east-1.amazonaws.com/default/claude-chat'


        def get_ai_response(obj):
            x = requests.post(url, json = obj)
            return x.content.decode("utf-8")

        if not st.session_state.get("input_text"):
            st.session_state.input_text = ""
        system_message_sql = """
            You are a {dialect} expert. You are interacting with a user who is asking you questions about the database.
            Based on the table schema below, write a SQL query that would answer the user's question.
            
            Here is the database schema:
            <schema>{table_info}</schema>
            
            Write ONLY THE SQL QUERY and nothing else. 
            Do not wrap the SQL query in any other text, not even backticks. Do not include newline character in sql and return as a single line.
            For example:
            Question: Name 10 artists
            SQL Query: <sql_query> SELECT Name FROM Artist LIMIT 10; <sql_query>
            Your turn:
            Question: {question}
            SQL Query:
            """

        system_message_full = """
            Based on the question from the user, sql_query, and sql_response, write a natural language response.
            Do not exaplain the whole process of extracting response. Only provide the info on database result without any other information.
            SQL Query: <sql_query> {query} </sql_query>
            User question: {question}
            SQL Response: {response}"""
        with st.sidebar:
            st.write("Sample Queries:")
            for q in questions:    
                if st.button(q):
                    st.session_state.input_text = q
        text_input = st.text_input("Enter Query", st.session_state.input_text)
        if text_input:
            st.session_state.input_text = text_input

        if len(st.session_state.input_text)>0:

            question = st.session_state.input_text
            db = load_data()
            prompt = PromptTemplate.from_template(system_message_sql)
            sys_message = prompt.format(dialect=db.dialect, table_info=db.get_table_info(),question=question)

            human_message = {"role": "user", "content": question}
            system_message = {"role": "system", "content": sys_message}


            sql_response = get_ai_response({"messages":[human_message, system_message]})
            sql_response = sql_response[1:-1].strip()
            sql_response = sql_response.replace("\\n", " ")
            #st.write(sql_response)
            db_res = db.run(sql_response)
            prompt = PromptTemplate.from_template(system_message_full)
            sys_message_txt = prompt.format(query=sql_response, response=db_res, question=question)
            system_message_full = {"role": "system", "content": sys_message_txt}
            #full_response = get_ai_response({"messages":[human_message, system_message_full]})
            #st.write(db_res)
            #st.write(full_response[1:-1].strip())
            con = sqlite3.connect("Chinook.db")
            df = pd.read_sql_query(sql_response, con)
            st.dataframe(
            df,
            hide_index=True, use_container_width=True)
            
            numerical_cols = list(df.select_dtypes(include='number').columns)
            categorical_cols = list(df.select_dtypes(include='category').columns)
            object_cols = list(df.select_dtypes(include='object').columns)
            merged_cols = categorical_cols + object_cols
            if len(numerical_cols) >= 1 and len(merged_cols) >= 1:
                for m_c in merged_cols:
                    st.bar_chart(df, x=m_c, y=numerical_cols)
            con.close()
