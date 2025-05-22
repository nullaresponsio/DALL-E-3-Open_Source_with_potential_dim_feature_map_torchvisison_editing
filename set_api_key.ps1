$key = 'sk-proj-wR2nqdtjOKNHAA8K64RLuYWLqH3-NFJPL-TmdcId4yxIb-WNDmW7zgGlXO9h2OBhsAtlPPyb7w9M4G0K0pK0S8KSqzV_0JhcNQA'
$env:OPENAI_API_KEY = $key
[Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $key, 'User')
