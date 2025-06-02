How to Deploy:

# 1. Navigate to serve directory
cd serve

# 2. Create a clean package folder
rm -rf package && mkdir package

# 3. Install dependencies into package (must use Linux env for compatibility with Lambda)
pip install fastapi mangum yfinance boto3 langgraph -t package

# 4. Copy your app code into package
cp main.py package/

# 5. Zip everything inside package
cd package
zip -r ../lambda.zip .

# 6. Deploy lambda.zip via Terraform
cd ../../infra
terraform init
terraform apply
Here you should see the output of {api_url}

# 7. Check Deployment
Go to the AWS Lambda Console and Confirm:
function name = stock-agent-api
Handler = main.handler
Runtime = Python 3.11

# 8. Deploy web application
Replace 'http://localhost:8000' to {api_url} in public/index.html and upload the index.html file to s3.
Grant "public access" permission to s3 file or set up aws cloudfront pointing to s3, then you will have a public address. 


