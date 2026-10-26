from dotenv import dotenv_values
vals = dotenv_values('c:/Users/KEERTHAN BM/OneDrive/Desktop/CricketIQ/.env')
uri = vals.get('MONGODB_URI', '')
import re
m = re.search(r'@([^/]+)/', uri)
if m:
    host = m.group(1)
    parts = host.split('.')
    cluster_name = parts[0]
    cluster_id = parts[1] if len(parts) > 1 else 'unknown'
    print(f'Cluster name: {cluster_name}')
    print(f'Atlas cluster identifier in URL: {cluster_id}')
    print()
    print('Action: In your browser, go to cloud.mongodb.com')
    print('Look at the URL - it should contain this cluster identifier.')
    print('If you see a different ID in the URL, you are in the WRONG project.')
    print()
    print('Correct project URL looks like:')
    print(f'  https://cloud.mongodb.com/v2/<project_id>#/clusters')
    print(f'  And the cluster listed should be: {cluster_name}')
