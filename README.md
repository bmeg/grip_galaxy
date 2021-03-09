
# GRaph Integration Platform for Galaxy

Prototype Galaxy interactive tool that runs a [Sifter](https://github.com/bmeg/sifter)
data loading playbook into a GRIP server. Once loaded the user will be able to
open up a JupyterLab server and query the database.

## Sample ETL

```yaml
class: Playbook

inputs:
  sifFile:
    type: File
    default: https://www.pathwaycommons.org/archives/PC2/v12/PathwayCommons12.All.hgnc.sif.gz

steps:
  - tableLoad:
      input: "{{inputs.sifFile}}"
      sep: "\t"
      columns: [_from, _label, _to]
      transform:
        - fork:
            transform:
              -
                - project:
                    mapping:
                      nodes: [{"_gid":"{{row._from}}"}, {"_gid":"{{row._to}}"}]
                - fieldProcess:
                    field: nodes
                    steps:
                      - distinct:
                          field: "{{row._gid}}"
                          steps:
                            - project:
                                mapping:
                                  _label: "Protein"
                            - emit:
                                name: vertex
              -
                - emit:
                    name: edge
```


### Example Query

```python
import gripql
conn = gripql.Connection()
G = conn.graph("graph")
list(G.query().V("BRCA1").outE().as_("a").out().as_("b").render(["$a._label", "$b._gid"]))
```

which returns
```python
[['controls-expression-of', 'AKR7A2'],
 ['controls-state-change-of', 'AKT1'],
 ['catalysis-precedes', 'APEX1'],
 ['catalysis-precedes', 'AQR'],
 ['controls-expression-of', 'ARID3B'],
 ['controls-state-change-of', 'ARNT'],
 ['controls-expression-of', 'ATF3'],
 ['controls-expression-of', 'ATM'],
 ['controls-state-change-of', 'ATP5PF'],
 ['controls-expression-of', 'ATR'],
 ['controls-state-change-of', 'BCL2'],
 ['controls-state-change-of', 'BID'],
 ['controls-expression-of', 'BIRC3'],
 ....
]
```

## Build container
```bash
docker build -t grip_galaxy .
```

## Test deployment

Configure Galaxy to allow for interactive tools:
```yaml
uwsgi:
  http: localhost:8080
  threads: 8
  http-raw-body: True
  offload-threads: 8
  master: true
  module: galaxy.webapps.galaxy.buildapp:uwsgi_app()
  interactivetools_map: database/interactivetools_map.sqlite
  python-raw: scripts/interactivetools/key_type_token_mapping.py
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(interactivetool\.localhost:8080)$ goto:itdomain
  route-run: goto:itdomainend
  route-label: itdomain
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(interactivetool\.localhost:8080)$ rpcvar:TARGET_HOST rtt_key_type_token_mapper_cached $1 $3 $2 $4 $0 5
  route-if-not: empty:${TARGET_HOST} httpdumb:${TARGET_HOST}
  route: .* break:404 Not Found
  route-label: itdomainend
  # Path-based is currently less functional and less tested than domain-based
  route: ^(/interactivetool/access/)([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)(()|(/.*)*)$ goto:itpath
  route-run: goto:itpathend
  route-label: itpath
  route: ^/interactivetool/access/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)(()|/.*)$ rpcvar:TARGET_HOST rtt_key_type_token_mapper_cached $2 $1 $3 $4 $0 5
  route-if: empty:${TARGET_HOST} goto:itpathfail
  route: ^/interactivetool/access/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)/([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)((()|/.*)*)$ rewrite:$4
  route-if: empty:${PATH_INFO} addvar:PATH_INFO=/
  route-run: seturi:${PATH_INFO}
  route-if-not: empty:${QUERY_STRING} seturi:${PATH_INFO}?${QUERY_STRING}
  route-if-not: empty:${TARGET_HOST} httpdumb:${TARGET_HOST}
  route-label: itpathfail
  route: .* break:404 Not Found
  route-label: itpathend
galaxy:
  interactivetools_enable: true
  # outputs_to_working_directory will provide you with a better level of isolation. It is highly recommended to set
  # this parameter with InteractiveTools.
  outputs_to_working_directory: true
  interactivetools_prefix: interactivetool
  interactivetools_map: database/interactivetools_map.sqlite
  # If you develop InteractiveTools locally and do not have a full FQDN you can
  # use an arbritrary one, e.g. 'my-hostname' here, if you set this hostname in your
  # job_conf.xml as well (see the corresponding comment). If running mac OS X, do not match the
  # "http://host.docker.internal:8080" used at galaxy_infrastructure_url in the galaxy.yml file,
  # and use an arbitrary name here instead.
  # Please make sure that in the local development case you use https://localhost:8080 to access
  # your Galaxy. http://my-hostname:8080 will not work.
  # galaxy_infrastructure_url: http://my-hostname:8080
```


Configure Galaxy `config/job_conf.xml` to handle interactive tools
```xml
<?xml version="1.0"?>
<job_conf>
    <plugins>
        <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="4"/>
    </plugins>
    <destinations default="docker_dispatch">
        <destination id="local" runner="local"/>
        <destination id="docker_local" runner="local">
          <param id="docker_enabled">true</param>
          <param id="docker_volumes">$galaxy_root:ro,$tool_directory:ro,$job_directory:rw,$working_directory:rw,$default_file_path:ro</param>
          <param id="docker_sudo">false</param>
          <param id="docker_net">bridge</param>
          <param id="docker_auto_rm">true</param>
          <param id="require_container">true</param>
          <param id="docker_set_user"></param>
		      <param id="local_slots">4</param>
        </destination>
        <destination id="docker_dispatch" runner="dynamic">
            <param id="type">docker_dispatch</param>
            <param id="docker_destination_id">docker_local</param>
            <param id="default_destination_id">local</param>
        </destination>
    </destinations>
</job_conf>
```

Copy `interactivetool_grip.xml` into `tools/interactive/`.

In the file `config/tool_conf.xml` add the line:
```xml
    <tool file="interactive/interactivetool_grip.xml" />
```
