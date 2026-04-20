# Lambda inference with container

## Environment variable

### AWS Configuration
`MODEL_BUCKET=your bucket model`<br/>
`MODEL_KEY=models/hybrid_model.pkl`

### Dynamo Tables
`USERS_TABLE=techmart-users`<br/>

## recommendation Test
### Method POST Testing
```json
{
  "user_id": "user_00001",
}
