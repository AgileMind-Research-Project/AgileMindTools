# import botocore 
# import botocore.session 
# import json
# from aws_secretsmanager_caching import SecretCache, SecretCacheConfig 

# def get_cred(tenant):
#     client = botocore.session.get_session().create_client('secretsmanager',region_name='ap-southeast-1')
#     cache_config = SecretCacheConfig()
#     cache = SecretCache( config = cache_config, client = client)
#     secret = cache.get_secret_string('tenant_'+tenant)
#     return json.loads(secret)   