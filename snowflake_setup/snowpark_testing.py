#%%
from snowflake.snowpark import Session
import requests
import json
from openai import OpenAI

CONNECTION_PARAMETERS = {
    "account": 'ahsorg-ahsprod',
    "user": 'KEVIN.LONERGAN@ALBERTAHEALTHSERVICES.CA',
    "role": 'RL_TEAM_JENKINS',
    "warehouse": 'WH_SMALL',
    "database": 'DB_TEAM_JENKINS',
    "schema": 'KL_TEST_JENKINS',
    "authenticator": 'externalbrowser'
}
session = Session.builder.configs(CONNECTION_PARAMETERS).create()

#%%
# Get JWT Token
session.sql(f"alter session set python_connector_query_result_format = json;").collect()

# Get the session token, which will be used for API calls for authentication
sptoken_data = session.connection._rest._token_request('ISSUE')
session_token = sptoken_data['data']['sessionToken']

# craft the request to ingress endpoint with authz
api_headers = {'Authorization': f'''Snowflake Token="{session_token}"'''}
api_headers['Content-Type'] = 'application/json'

#%%
# Modify OpenAI's API key and API base to use vLLM's API server.  We are not actually calling openAI
prompt = "What is it like in Alberta?"
openai_api_key = "EMPTY"
openai_api_base = "https://gtj4apn-ahsorg-ahsprod.snowflakecomputing.app/v1"


client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
    default_headers=api_headers
)
# %%
outputs = client.completions.create(model="/models/mistral/",
                                      prompt=prompt, 
                                      max_tokens=500,
                                      n=1,
                                      stop=None,
                                      temperature=0)

# print outputs text
# %%
print(outputs.choices[0].text)

# %% Try real example using Rheumatology use case of extracting dx from consult and progress note documents
session.use_role('RL_TEAM_DATA_ANALYTICS_HUB')
session.use_database('DB_SOURCE_EPIC_CLARITY_REPORT')
session.use_schema("REPORT")

#%% Get recent consult and progress notes authored by Dr. Claire Barber
from snowflake.snowpark.functions import listagg
sql =  """
    SELECT
    N.NOTE_ID,
    NT.NAME "NOTE_TYPE",
    NS.NAME "NOTE_STATUS",
    TXT.LINE,
    TXT.NOTE_TEXT
    FROM PAT_ENC_HSP PE
    JOIN PATIENT P
    ON PE.PAT_ID = P.PAT_ID
    JOIN HNO_INFO N
    ON PE.PAT_ENC_CSN_ID = N.PAT_ENC_CSN_ID
    JOIN CLARITY_EMP EMP
    ON N.CURRENT_AUTHOR_ID = EMP.USER_ID
    LEFT JOIN ZC_NOTE_TYPE_IP NT
    ON N.IP_NOTE_TYPE_C = NT.TYPE_IP_C
    LEFT JOIN NOTE_ENC_INFO N2
    ON N.NOTE_ID = N2.NOTE_ID
    LEFT JOIN ZC_NOTE_STATUS NS
    ON N2.NOTE_STATUS_C = NS.NOTE_STATUS_C
    JOIN HNO_NOTE_TEXT TXT
    ON N.NOTE_ID = TXT.NOTE_ID
    WHERE N.CURRENT_AUTHOR_ID = '88000' -- Dr. B.
    AND NT.NAME IN ('Progress Notes', 'Consults')
    AND N.CREATE_INSTANT_DTTM > TO_DATE('01-NOV-2023', 'DD-MON-YYYY')
    AND N2.MOST_RECENT_CNCT_YN = 'Y'
    ORDER BY NOTE_ID, LINE
    """

note_df = session.sql(sql).collect()

                                                                               
sample_rheumatology_prompt = """
Given a medical note written by a rheumatologist, your task is to analyze the text to determine if the information suggests a diagnosis of Rheumatoid Arthritis (RA), Systemic Lupus Erythematosus (Lupus), or indicates a different rheumatological condition. Consider key clinical findings, patient symptoms, laboratory test results, and any other pertinent details mentioned in the note. Provide your analysis by categorizing the likely diagnosis based on the evidence provided in the note. Your response should include: 
Diagnosis Determination: State if the medical note suggests Rheumatoid Arthritis, Lupus, or another rheumatological condition. If another condition is suspected, specify what that might be based on the information provided.
Key Evidence: Summarize the critical pieces of evidence from the note that support your determination. This could include specific symptoms, diagnostic test results, patient history, or any other relevant clinical information mentioned.
Confidence Level: Briefly describe your level of confidence in the diagnosis determination and why. If the information is insufficient to make a clear determination, explain what additional information would be helpful.
Please ensure your analysis is concise, focused on the information provided in the medical note, and adheres to medical ethics and privacy standards by not making assumptions beyond the data presented."""


#%%

