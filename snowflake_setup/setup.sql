--Confirm db/schema 
USE ROLE RL_TEAM_JENKINS;
USE DB_TEAM_JENKINS.KL_TEST_JENKINS;  
--Create an Image Repo.  
CREATE IMAGE REPOSITORY KL_MISTRAL_VLLM_REPOSITORY;
SHOW IMAGE REPOSITORIES;

--Upload image to this repo
-- 1. Build the Docker image
--    docker build --rm --platform linux/amd64 -t vllm_snowflake .
                             
-- 2. Tag and push it to SPCS
--    docker tag vllm_snowflake ahsorg-ahsprod.registry.snowflakecomputing.com/db_team_jenkins/kl_test_jenkins/kl_mistral_vllm_repository
--    docker login 
--    docker push ahsorg-ahsprod.registry.snowflakecomputing.com/db_team_jenkins/kl_test_jenkins/kl_mistral_vllm_repository
   
--Confirm image uploaded
CALL SYSTEM$REGISTRY_LIST_IMAGES('/DB_TEAM_JENKINS/KL_TEST_JENKINS/KL_JENKINS_REPOSITORY');

--Create a stage to hold YAML FILES, MODEL FILES, AND FILES FOR THIS CONTAINER (IF NOT ALREADY EXISTING)
SHOW STAGES;
CREATE STAGE KL_YAML_FILES ENCRYPTION = (type = 'SNOWFLAKE_SSE');
CREATE STAGE MODELS ENCRYPTION ENCRYPTION = (type = 'SNOWFLAKE_SSE');
CREATE STAGE KL_MISTRAL_VLLM_REPOSITORY ENCRYPTION = (type = 'SNOWFLAKE_SSE');

--Put the yaml file in the stage
PUT 'file://C:\\Users\\klonergan\\Documents\\MyVSCodeRepo\\mistral_vllm_demo\\mistral_vllm_spec.yaml' '@KL_YAML_FILES' AUTO_COMPRESS=false OVERWRITE=true;


--Confirm compute pool available (Kamran / Snowflake Admin needs to create this)
SHOW COMPUTE POOLS;

--Confirm external access (Kamran configured this to allow external access to hugging face). 

SHOW EXTERNAL ACCESS INTEGRATIONS; 
--TODO: Investigate why this external access does not work with vllm in docker entrypoint file / for now, manually added mistral to stage and used path reference.  Can do this via terminal in Jupyter notebook on SPCS or via another machine.

CREATE SERVICE KL_VLLM_MISTRAL
IN COMPUTE POOL GPU_NV_S
FROM @KL_YAML_FILES
SPECIFICATION_FILE = 'mistral_vllm_spec.yaml'
MIN_INSTANCES = 1
MAX_INSTANCES = 1
EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION); 

--Check Service Status
select 
  v.value:containerName::varchar container_name
  ,v.value:status::varchar status  
  ,v.value:message::varchar message
from (select parse_json(system$get_service_status('KL_VLLM_MISTRAL'))) t, 
lateral flatten(input => t.$1) v;

SHOW ENDPOINTS IN SERVICE KL_VLLM_MISTRAL;

--Check Service Logs
SELECT SYSTEM$GET_SERVICE_LOGS('KL_VLLM_MISTRAL', '0', 'vllm', 1000);

--DROP SERVICE KL_VLLM_MISTRAL;

--show files in stage KL_MISTRAL_FILES_STAGE
LIST @MODELS;

--update if changes made to yaml file or docker image
ALTER SERVICE KL_VLLM_MISTRAL
FROM @KL_YAML_FILES
SPECIFICATION_FILE = 'mistral_vllm_spec.yaml'
EXTERNAL_ACCESS_INTEGRATIONS = (LLM_ACCESS_INTEGRATION); 

ALTER SERVICE KL_VLLM_MISTRAL SUSPEND;
ALTER SERVICE KL_VLLM_MISTRAL RESUME;
  
--TODO: CREATE A SERVICE FUNCTION TO ALLOW ACCESS TO THE SERVICE FROM SQL
CREATE FUNCTION MISTRAL_LLM(prompt text)
returns text
service=llama_2
endpoint=chat;