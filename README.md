Developed a serverless AI agent on AWS using FastAPI and LangGraph to handle natural language queries for real-time and historical stock prices. The backend integrates AWS Lambda and Bedrock, with infrastructure defined in Terraform.

## How to Deploy:

### 1. Navigate to serve directory and create a clean package folder
<pre>
  cd serve  
  rm -rf package && mkdir package  
</pre>

### 2. Install dependencies into package
<pre>
  pip install fastapi mangum yfinance boto3 langgraph -t package  
</pre>

### 3. Copy your app code into package
<pre>
  cp main.py package/
</pre>  

### 4. Zip everything inside package
<pre>
  cd package
  zip -r ../lambda.zip .
</pre>

### 5. Deploy lambda.zip via Terraform
<pre>
  cd ../../infra  
  terraform init  
  terraform apply  
</pre>
Here you should see the output for service: {api_url}  

### 6. Check backend deployment
Go to the AWS Lambda console and confirm:
<pre>
  function name = stock-agent-api
  Handler = main.handler
  Runtime = Python 3.11  
</pre>
If they all exist, it means the deployment was successful.

### 7. Deploy web application
Replace {api_url} in public/index.html with production api_url from step 5 and then upload the file to s3.  
Grant "public access" permission to s3 file or set up aws cloudfront pointing to s3, then you will have a public address.  

### 8. Test web application
Open the public URL in your browser—you’ll see an input box. Enter your stock-related questions there. Currently, the tool supports two types of queries: the current price and historical prices for a single stock.  
  
Sample questions:  
1) What is the stock price for Amazon right now?  
2) What were the stock prices for Amazon in Q4 last year?  

