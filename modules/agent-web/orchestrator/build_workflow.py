#!/usr/bin/env python3
"""Dựng JSON workflow n8n 'webhook tạo nhân viên (agent + Telegram + MCP)' từ tham số tenant. In ra stdout.
Đầu vào (đều trong thư mục tenant): users.json (add_caller.py), gateway_pub.pem (keygen.py), mcp_profile.json (tuỳ chọn).
Không có mật khẩu gốc trong workflow: chỉ băm mật khẩu + secret HMAC (cần để kiểm chữ ký)."""
import json, sys, os
import awconf as A
path = A.need('AW_WEBHOOK_PATH'); dt = A.need('AW_REGISTRY_TABLE_ID'); dtk = A.need('AW_CHANNEL_TABLE_ID')
users_file = A.AWDIR + '/users.json'
if not os.path.exists(users_file): sys.exit('LOI chua co ben goi: kit run agent-web add-caller <ten>')
pubf = A.AWDIR + '/gateway_pub.pem'
if not os.path.exists(pubf): sys.exit('LOI chua co khoa cong khai: kit run agent-web keygen')
pub = open(pubf, encoding='utf-8').read().strip()
assert pub.startswith('-----BEGIN PUBLIC KEY-----') and '`' not in pub
U = json.load(open(users_file, encoding='utf-8'))
cred = ''
D = os.path.join(os.environ.get('KIT_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))), 'modules', 'agent-web', 'n8n')
_prof = A.AWDIR + '/mcp_profile.json'
SCOPES = sorted(json.load(open(_prof, encoding='utf-8'))['scopes']) if os.path.exists(_prof) else []
code = lambda f: open(os.path.join(D, 'code', f), encoding='utf-8').read()
cols = ['user_id', 'agent_id', 'ho_ten', 'email', 'phong_ban', 'gateway_id', 'trang_thai', 'ghi_chu']
dtref = {'__rl': True, 'mode': 'id', 'value': dt}
def node(name, typ, ver, pos, params, **kw):
    n = {'id': name.encode('utf-8').hex()[:32].ljust(32, '0'), 'name': name, 'type': typ, 'typeVersion': ver, 'position': pos, 'parameters': params}
    n.update(kw); return n
vals = {'user_id': '={{ $json.user_id }}', 'agent_id': '={{ $json.agent_id }}', 'ho_ten': '={{ $json.ho_ten }}',
        'email': '={{ $json.email }}', 'phong_ban': '={{ $json.phong_ban }}', 'gateway_id': '',
        'trang_thai': 'cho_tao', 'ghi_chu': '={{ "tao qua webhook " + $now.toISO() }}'}
Q = '$("Quyết định").first().json'
colsk = ['user_id', 'agent_id', 'telegram_bot_username', 'telegram_user_id', 'mcp_url', 'mcp_pham_vi', 'mcp_het_han', 'bi_mat', 'trang_thai', 'cap_nhat_luc', 'ghi_chu']
valsk = {c: '={{ ' + Q + '.' + c + ' }}' for c in ['user_id', 'agent_id', 'telegram_bot_username', 'telegram_user_id', 'mcp_url', 'mcp_pham_vi', 'mcp_het_han', 'bi_mat']}
valsk.update({'trang_thai': 'cho_gan', 'cap_nhat_luc': '={{ $now.toISO() }}', 'ghi_chu': '={{ "webhook goi boi " + ' + Q + '.goi_boi }}'})
dtkref = {'__rl': True, 'mode': 'id', 'value': dtk}
schema = lambda cs: [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True, 'type': 'string', 'canBeUsedToMatch': True} for c in cs]
nodes = [
  node('Webhook', 'n8n-nodes-base.webhook', 2, [0, 0], {'httpMethod': 'POST', 'path': path, 'responseMode': 'responseNode', 'authentication': 'basicAuth' if cred else 'none', 'options': {'rawBody': True}}, webhookId=path, **({'credentials': {'httpBasicAuth': {'id': cred, 'name': 'Agent Web webhook (Hrm)'}}} if cred else {})),
  node('Xác thực', 'n8n-nodes-base.code', 2, [220, 0], {'jsCode': code('xac_thuc.js').replace('__USERS__', json.dumps(U['users'])).replace('__SALT__', U['salt']).replace('__PUBKEY__', pub).replace('__SCOPES__', json.dumps(SCOPES))}),
  node('Hợp lệ?', 'n8n-nodes-base.if', 2, [440, 0], {'conditions': {'options': {'caseSensitive': True, 'typeValidation': 'loose', 'version': 2}, 'combinator': 'and',
      'conditions': [{'id': 'c1', 'leftValue': '={{ $json.ok }}', 'rightValue': True, 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}]}, 'options': {}}),
  node('Tìm user', 'n8n-nodes-base.dataTable', 1, [660, -100], {'resource': 'row', 'operation': 'get', 'dataTableId': dtref, 'matchType': 'allConditions',
      'filters': {'conditions': [{'keyName': 'user_id', 'condition': 'eq', 'keyValue': '={{ $json.user_id }}'}]}}, alwaysOutputData=True),
  node('Quyết định', 'n8n-nodes-base.code', 2, [880, -100], {'jsCode': code('quyet_dinh.js')}),
  node('User mới?', 'n8n-nodes-base.if', 2, [1100, -100], {'conditions': {'options': {'caseSensitive': True, 'typeValidation': 'loose', 'version': 2}, 'combinator': 'and',
      'conditions': [{'id': 'c2', 'leftValue': '={{ $json._new }}', 'rightValue': True, 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}]}, 'options': {}}),
  node('Ghi registry', 'n8n-nodes-base.dataTable', 1, [1320, -200], {'resource': 'row', 'operation': 'insert', 'dataTableId': dtref,
      'columns': {'mappingMode': 'defineBelow', 'value': vals, 'matchingColumns': [],
                  'schema': [{'id': c, 'displayName': c, 'required': False, 'defaultMatch': False, 'display': True, 'type': 'string', 'canBeUsedToMatch': True} for c in cols],
                  'attemptToConvertTypes': False, 'convertFieldsToString': False}, 'options': {}}),
  node('Có kênh?', 'n8n-nodes-base.if', 2, [1540, -100], {'conditions': {'options': {'caseSensitive': True, 'typeValidation': 'loose', 'version': 2}, 'combinator': 'and',
      'conditions': [{'id': 'c3', 'leftValue': '={{ ' + Q + '.co_kenh }}', 'rightValue': True, 'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}]}, 'options': {}}),
  node('Ghi kênh', 'n8n-nodes-base.dataTable', 1, [1760, -200], {'resource': 'row', 'operation': 'upsert', 'dataTableId': dtkref, 'matchType': 'allConditions',
      'filters': {'conditions': [{'keyName': 'user_id', 'condition': 'eq', 'keyValue': '={{ ' + Q + '.user_id }}'}]},
      'columns': {'mappingMode': 'defineBelow', 'value': valsk, 'matchingColumns': [], 'schema': schema(colsk),
                  'attemptToConvertTypes': False, 'convertFieldsToString': False}, 'options': {}}),
  node('Kết quả', 'n8n-nodes-base.code', 2, [1980, -100], {'jsCode': code('ket_qua.js')}),
  node('Trả lời', 'n8n-nodes-base.respondToWebhook', 1.1, [2200, 0], {'respondWith': 'json', 'responseBody': '={{ JSON.stringify($json.out) }}',
      'options': {'responseCode': '={{ $json.http_status }}'}}),
]
c = lambda *targets: {'main': [[{'node': t, 'type': 'main', 'index': 0} for t in grp] for grp in targets]}
connections = {
  'Webhook': c(['Xác thực']), 'Xác thực': c(['Hợp lệ?']), 'Hợp lệ?': c(['Tìm user'], ['Trả lời']),
  'Tìm user': c(['Quyết định']), 'Quyết định': c(['User mới?']), 'User mới?': c(['Ghi registry'], ['Có kênh?']),
  'Ghi registry': c(['Có kênh?']), 'Có kênh?': c(['Ghi kênh'], ['Kết quả']), 'Ghi kênh': c(['Kết quả']), 'Kết quả': c(['Trả lời']),
}
names = {n['name'] for n in nodes}
for k, v in connections.items():
    assert k in names, k
    for grp in v['main']:
        for t in grp: assert t['node'] in names, t
settings = {'executionOrder': 'v1', 'timezone': A.C.get('TIMEZONE', 'Asia/Ho_Chi_Minh')}
if A.C.get('AW_ERROR_WORKFLOW_ID'): settings['errorWorkflow'] = A.C['AW_ERROR_WORKFLOW_ID']
body = {'name': A.C.get('AW_WORKFLOW_NAME', 'Tool Openclaw - Agent Web Tạo user'), 'nodes': nodes, 'connections': connections, 'settings': settings}
json.dump(body, sys.stdout, ensure_ascii=False)
