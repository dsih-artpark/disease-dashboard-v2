# Disease Dashboard

## Documentation (WIP)

### Granting Permissions
```
python3 -m server_admin.grant_permission userid@email.com tenant_id permission_name
# e.g.:
python3 -m server_admin.grant_permission dmo@gmail.com ka predictions
python3 -m server_admin.grant_permission dmo@gmail.com ka user_management
python3 -m server_admin.grant_permission dmo@gmail.com ka report_download
```

### Revoking Permissions
```
python3 -m server_admin.revoke_permission userid@email.com tenant_id permission_name
# e.g.:
python3 -m server_admin.revoke_permission dmo@gmail.com ka predictions
python3 -m server_admin.revoke_permission dmo@gmail.com ka user_management
python3 -m server_admin.revoke_permission dmo@gmail.com ka report_download
```

## Known Pending Items

- Add Disease Stage Definitions
- Public View
- Make Disease Stage Agnostic
- Documentation / Document every file
