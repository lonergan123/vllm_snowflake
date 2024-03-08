# mistral_vllm_demo
This application container is intended for installing llm inference in snowpark container services using vllm.  It is loosely based on the code at https://github.com/edemiraydin/mistral_vllm_demo/tree/main --> but is not specific to mistral. Snowflake specific setup instructions are included in the snowflake_setup\setup.sql file.
For docker config:
1. Build the Docker image
   docker build --rm --platform linux/amd64 -t vllm_snowflake .
                             
2. Tag and push it to Snowpark container services image repo
   docker tag vllm_snowflake <SPCS image repo URL>
   docker login 
   docker push <SPCS image repo URL>
   