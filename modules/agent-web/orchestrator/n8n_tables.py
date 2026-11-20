#!/usr/bin/env python3
"""Tạo 2 n8n Data table (registry, channel) nếu chưa có id. In ra id để điền: kit enable agent-web --set AW_REGISTRY_TABLE_ID=... 
CHƯA THỬ THẬT: endpoint tạo Data table qua public API tuỳ phiên bản n8n. Nếu lỗi: tạo tay trong n8n UI với đúng tên cột bên dưới (kiểu string)."""
import sys
import awconf as A
T = {"agent_registry": ["user_id", "agent_id", "ho_ten", "email", "phong_ban", "gateway_id", "trang_thai", "ghi_chu"],
     "agent_kenh": ["user_id", "agent_id", "telegram_bot_username", "telegram_user_id", "mcp_url", "mcp_pham_vi", "mcp_het_han", "bi_mat", "trang_thai", "cap_nhat_luc", "ghi_chu"]}
for name, cols in T.items():
    try:
        d = A.n8n("POST", "/data-tables", {"name": name, "columns": [{"name": c, "type": "string"} for c in cols]})
        print(f"OK {name}: id={d.get('id')}")
    except Exception as e:
        print(f"LOI {name}: {str(e)[:200]}\n  -> tao tay trong n8n: Data tables > Create, ten '{name}', cot string: {', '.join(cols)}")
