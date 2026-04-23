# Lambda Inference with Container

## Environment variable

### AWS Configuration
`MODEL_BUCKET=your bucket model`<br/>
`MODEL_KEY=models/hybrid_model.pkl`

### Dynamo Tables
`PRODUCTS_TABLE=ProductEmbeddings`<br/>

## API Endpoint
### POST /api/recommend
```json
{
  "user_id": "user_00001",
}
```
## Build image
### Use this command to build the docker image for lambda! (change the image name and tag)
```bash
docker buildx build --platform linux/amd64 --provenance=false -t <docker-image:test> .
```
