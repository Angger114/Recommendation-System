FROM public.ecr.aws/lambda/python:3.13

# install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy source code
COPY lambda_function.py .
COPY model.py .

# command lambda
CMD ["lambda_function.lambda_handler"]