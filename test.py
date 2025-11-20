import requests

dataset_id = "748e02f2-3b11-4194-a5b7-e8063383bce6"
group_id = "ca8a6029-6b63-4508-8ce6-74f70c84eb97"

res = requests.get(
        f'https://api.powerbi.com/v1.0/myorg/groups/{group_id}/datasets/{dataset_id}/datasources',
        headers={'Authorization': token}
)