# Installing and switching providers

## Switching HACS providers safely

The upstream repository and a fork can both advertise the same
`mylight_systems` domain. Their downloads then target the same
`custom_components/mylight_systems` directory: installing or updating either can
replace the other's code. The running process can retain previously loaded code,
so currently working entities do not prove which code the next restart will load.

Keep only one active HACS provider for this domain. Before changing providers,
back up the integration files and the Home Assistant configuration. Removing an
obsolete HACS download deletes the shared code directory; reinstall the intended,
validated fork **before** reloading the integration or restarting Home Assistant.
Do not remove the configured mylight integration or its entities: retaining the
config entry and unique IDs preserves existing entity IDs, history and dashboard
references.

Before the planned reload, verify the installed version and expected modules,
check the Home Assistant configuration, and keep a rollback copy. After loading
the intended code, verify the grid and water-heater sensors and GreenPlay status.
A pull-request merge alone does not update an installed release; publish and
select the intended fork release through the normal reviewed release process.
