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
st.write(
    """
    This app visualizes data from CHINOOK database (https://www.kaggle.com/datasets/nancyalaswad90/chinook-sample-database)
    It includes 11 tables and Over 15,000 rows of data.
    """
)

if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None

if not st.session_state.api_key:
    #with st.sidebar:
    api_key=st.text_input("Enter password to get started:", type="password")
    if api_key == "F@k3pa$$word":
        st.session_state['api_key'] =api_key
        st.rerun()

if st.session_state['api_key']:
    questions = ["Find all albums for the artist 'AC/DC'.",
        "Find the total duration of all tracks.",
        "List all customers from Canada.",
        "Find the total number of invoices.",
        "List top 5 tracks that are longer than 5 minutes.",
        "Who are the top 5 customers by total purchase?"]

    url = 'https://f4wo0au9r5.execute-api.us-east-1.amazonaws.com/default/claude-chat'

    def load_data():
        db = SQLDatabase.from_uri("sqlite:///Chinook.db")
        return db

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
        
        df_numerical_features = df.select_dtypes(include='number')
        df_categorical_features = df.select_dtypes(include='category')
        st.write(df_numerical_features)
        st.write(df_categorical_features)
        if len(df_numerical_features) > 1 and len(df_categorical_features) > 1:
            st.bar_chart(df, x=df_categorical_features[0], y=df_numerical_features)
        con.close()
