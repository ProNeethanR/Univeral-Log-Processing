# ULPF Recovery Manifest

Generated: 2026-09-22
Repository: `P:\Univeral Log Processing`
Current HEAD: `95ba189`
Archive scope: complete current worktree contents excluding `.git` history; includes tracked, untracked, ignored recovery files, `ulpf`, and `t -q`.

## Worktree status

```text
## main...origin/main
 M contracts/event_contract.schema.json
 M src/api/main.py
 M src/api/models.py
 M src/api/services/event_service.py
 M src/normalization/mapper.py
 M src/registry/__init__.py
 M src/vault/store.py
 M tests/integration/test_api_events.py
 M tests/integration/test_syslog_pipeline.py
?? recovery-manifest.md
?? repository-baseline-reconciliation-plan.md
?? t -q
?? tests/normalization/test_context_injection.py
?? tests/normalization/test_enrichment_provenance.py
?? tests/registry/test_source_profile.py
?? ulpf/
?? worktree-provenance-audit.md
```

The manifest and archive verification report are recovery documentation, not implementation changes. The status above reflects the manifest's creation-time state; the final report is created afterward.

## Inventory counts

- Total preserved files: 124
- Tracked modified: 9
- Tracked unchanged: 50
- Untracked: 9, including this manifest at creation time
- Ignored recovery files: 56
- Archive excludes `.git` only.

## Validation evidence

- Current HEAD: `95ba189`
- Focused regression command: `PYTHONPATH=. pytest tests/registry/test_source_profile.py tests/normalization/test_context_injection.py tests/normalization/test_enrichment_provenance.py tests/integration/test_syslog_pipeline.py -q`
- Focused result: `18 passed in 0.91s`
- Full regression command: `PYTHONPATH=. pytest -q`
- Full result: `91 passed in 5.67s`
- Collection result: `91 tests collected in 2.18s`
- Failures: 0
- Errors: 0
- Skipped: 0
- Pytest warnings: 0
- Diff check: `git diff --check` passed; Git emitted only the existing LF-to-CRLF warning for `tests/integration/test_syslog_pipeline.py`.

## Recovery categories

### Completed Phase 1

- `contracts/event_contract.schema.json`
- `src/api/models.py`
- `src/api/services/event_service.py`
- `tests/integration/test_api_events.py`

### Existing pre-Phase-1 or parallel work

- `src/api/main.py`
- `src/vault/store.py`, pending explicit phase ownership

### Phase 2 registry/source-profile candidate work

- `src/registry/__init__.py`
- `src/normalization/mapper.py`
- `tests/registry/test_source_profile.py`
- `tests/normalization/test_context_injection.py`
- The source-profile portions of `tests/integration/test_syslog_pipeline.py`

### Later normalization/provenance work

- `tests/normalization/test_enrichment_provenance.py`
- The broader provenance portions of `tests/integration/test_syslog_pipeline.py`

### Historical duplicate

- `ulpf/`, including its decision documents and ignored pytest cache files. It is not the active source tree.

### Accidental/unrelated artifact

- `t -q`, containing pager help output.

### Recovery documentation

- `worktree-provenance-audit.md`
- `repository-baseline-reconciliation-plan.md`
- `recovery-manifest.md`

## Unresolved ambiguities

1. `src/api/main.py` needs explicit ownership classification against Phase 1 API compatibility.
2. `src/vault/store.py` needs explicit assignment to Phase 3/4 or documented contract-support status.
3. `tests/normalization/test_context_injection.py` contains a placeholder test using `pass`.
4. `ulpf/` must be checked for any current-only content before cleanup approval; its current visible content is historical decision documentation plus ignored pytest cache data.
5. The mixed worktree has not been separated or committed; all implementation changes remain recoverable only as a combined working-tree state until an approved checkpoint is created.

## Complete file inventory

CSV columns are: relative path, file type, size in bytes, SHA-256, Git status/category.

```csv
Path,Type,Size,SHA256,GitCategory
.gitignore,Git ignore file,4878,E79A6F863548FB0A68E5FF273E8D896EEFEAE405079FF972FA35A090205D2E8C,tracked unchanged
.pytest_cache/.gitignore,Git ignore file,39,E7C6BB30148CF667606DCD63E7CA77ACAA3CFB0C8303BF09E6419E1E1669DC6D,ignored recovery file
.pytest_cache/CACHEDIR.TAG,Cache metadata,191,37DC88EF9A0ABEDDBE81053A6DD8FDFB13AFB613045EA1EB4A5C815A74A3BDE4,ignored recovery file
.pytest_cache/README.md,Markdown documentation,310,420E808D79A6C25D3CDA0AF33BC4782314A14949866682C68CE8149E89B66B70,ignored recovery file
.pytest_cache/v/cache/lastfailed,Other file,2,44136FA355B3678A1146AD16F7E8649E94FB4FC21FE77E8310C060F61CAAFF8A,ignored recovery file
.pytest_cache/v/cache/nodeids,Other file,7440,FABA0F98DB67478F9A5C3E801F917B1C75715B550BB2B1C078FD7DFFA4A843ED,ignored recovery file
contracts/event_contract.schema.json,JSON data/contract,4489,B40B048948521D4724E2A7798CB16F0F0E66683A2DC061DC6E94A974F8F2C8CF,tracked modified
contracts/parser_mapping.schema.json,JSON data/contract,2491,C67D3B8526293E3A15122A7A605622702E9CE45E6F51572FA6F1919C1EA9DDCA,tracked unchanged
contracts/registry_api.md,Markdown documentation,1650,2857644FDAD0BE494AC96BABB259CE18C9591B114635BE95E58E461943EC9F7F,tracked unchanged
contracts/source_context.md,Markdown documentation,3857,157D958D0C2951FDF21E1F7CEE8406BA023AD33ADD85B2F9E06EEC93A5D01FC4,tracked unchanged
contracts/source_context.schema.json,JSON data/contract,1727,AEAC83CAC2F347BF36CEF2661D768B6F133FD9C2833CFA96C5D5875B405009A6,tracked unchanged
docker-compose.yml,YAML configuration,0,E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855,tracked unchanged
docs/architecture.md,Markdown documentation,0,E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855,tracked unchanged
fixtures/expected/cef/cef-real-001.json,JSON data/contract,10741,5655ABC9C62E2A7205B0B48B28FEEC7CED5E5DCF055CC18C046472539402F715,tracked unchanged
fixtures/expected/syslog/syslog-001.json,JSON data/contract,109843,55F695EAB2FA6645C203D94A87308E0C9765BE41CAF542C5F67D7202E26F8431,tracked unchanged
fixtures/expected/vendor/fortigate-001.json,JSON data/contract,77223,2326827A368A76C6E9DADEBD554A29043A79C35942A6B054D78A95A0582C8F0A,tracked unchanged
fixtures/ground_truth/cef/cef-real-001.json,JSON data/contract,16722,5650F5E252A493A69B24FA13853C0B37DFBDA1D5A4D9C1B5E7D9C12FDEE137DD,tracked unchanged
fixtures/ground_truth/syslog/syslog-001.json,JSON data/contract,177821,F85A9E552B642F7DAF766D760FA77762DB804F0A572828FDD3655AE792EF8466,tracked unchanged
fixtures/ground_truth/vendor/fortigate-001.json,JSON data/contract,155562,C2E6A05A1151D9591F1F9AD8F4601EC2E5908D7F96B46B10D2AF1B4DACDA789A,tracked unchanged
fixtures/manifest.json,JSON data/contract,4501,CE640F0A4BCAB0595F4B5A4E9A6EA1D9DE5EF6236120DF1F712449E5734177D3,tracked unchanged
fixtures/provenance/README.md,Markdown documentation,3742,D8A3A1CA2EDEB81734674C2B9B15E782BFE1663FCFCE81EE66AD377A13012F84,tracked unchanged
fixtures/raw/cef/cef-real-001.log,Log data,1629,CA37D406D7D67ECFCD864EF0864A7A3727F8F947AD9457448C97C9D5B46608B1,tracked unchanged
fixtures/raw/cef/doc_reference/cef-doc-examples.log,Log data,1105,BF84DB1E910664E548BC71952FD4699CE497AD9EA4A4E9926462FD18AF6826DF,tracked unchanged
fixtures/raw/syslog/syslog-001.log,Log data,5330,A3783B7C387F7248D8C90C315B9B06A73BF4F7E6D0A6631B0A2449AFD5706552,tracked unchanged
fixtures/raw/vendor/fortigate-001.log,Log data,8926,21A07D34CE4BA0235EA2678BB5EC682DBBA0C39CB936F9CDCA5772146BEAEC2F,tracked unchanged
fixtures/SHA256SUMS,Other file,451,83269C20EA49DEF17D403498C202935F1F0A2CA924F0F8DF7219377E53333E1C,tracked unchanged
fixtures/STATUS.md,Markdown documentation,3229,CC73C51DB66F7B034A69FEA0EE402CA46B1971EDF298E5896A1D1A379E18ED62,tracked unchanged
honeynet.log,Log data,68104522,BF66A67226B07427C98E4FA228AD4B949B13771E69E99FEE6D43429E0AB9DAC4,tracked unchanged
honeynet.log.gz,GZip archive,3905534,389EC4249F52CA9FD7160213499D6942F064591A51BF9798A2AD4EC7D0FD5B93,tracked unchanged
parsers/syslog.yaml,YAML parser/config,3568,48179506211DEF3CBF1A21D9EF9D664294C00CC7365FEC251951BC22094C475D,tracked unchanged
README.md,Markdown documentation,10684,F76DDA218E5802923982E2D245A07B1209C99BAA3CE8655A88A752F3570E71AC,tracked unchanged
repository-baseline-reconciliation-plan.md,Markdown documentation,16636,3F02FA73FBE423BD89B82F91FADD281134ED1C10F1EB0D5C30D70DDF9954B445,untracked
requirements.txt,Plain text,217,BB533F99982DF3E057BA3C55B621791B19AA82B85A3785218DDE56C44E86BA36,tracked unchanged
schema/ocsf/ocsf_schema.json,JSON data/contract,1842134,6CCFF0F70B6216ABC8F82BE3756A9A167662A535C64A6A60DF111B0DB363E3E2,tracked unchanged
schema/ocsf/README.md,Markdown documentation,1163,AC3CE83E509449CB94A4928F2EC4413EB634018411EF404912E0C909DEA00E36,tracked unchanged
schema/OCSF_VERSION.md,Markdown documentation,778,D38C13201E8BB0A01CB803245699C5BD057C285E689B541CBD81EDB7D941036A,tracked unchanged
schema/OUTCOME_DEFINITIONS.md,Markdown documentation,2973,083787A10E5F7B2BCB82F66B5CA55D75052636FE236BCFFAF5C329DAF0E0868A,tracked unchanged
src/api/__init__.py,Python source/test,8,74FFBBD35E7E956EE34584AAF55D466A693A20147F400A4EC3528C0AF8BB59C1,tracked unchanged
src/api/__pycache__/__init__.cpython-311.pyc,Python bytecode,155,4B8214B82CC865D7B3F63289F641FDE265F164209ABA3520DC2DA415033DB979,ignored recovery file
src/api/__pycache__/main.cpython-311.pyc,Python bytecode,7354,5AA4C777FE842A5E80EE483BDF7326FFD4006B7D7FEE0FD323F08F6A86279AE6,ignored recovery file
src/api/__pycache__/models.cpython-311.pyc,Python bytecode,9266,7C820E4023EC73CC50DC004D06CF326DA3921508CAF584BFC352390D36F430C7,ignored recovery file
src/api/main.py,Python source/test,4752,4FDB941DB28DD2AD840836ECD5412F39248B4FFA113EF62854E152F337341962,tracked modified
src/api/models.py,Python source/test,4998,4FC9FE4F833934E58321607C68D96EC8F71F15B9CFE3311DF3BC084C56379E0E,tracked modified
src/api/services/__init__.py,Python source/test,32,85E3288FD52E036E33231315FFD39489DCA9998C1C17AADFA6C4F00982AAF527,tracked unchanged
src/api/services/__pycache__/__init__.cpython-311.pyc,Python bytecode,208,7FD6E74DA28E4B5AD464C01124D4281BBF09317FC02E5C6678A13635ACBB32D5,ignored recovery file
src/api/services/__pycache__/event_service.cpython-311.pyc,Python bytecode,13654,5E89B5111E752334FDBF1CEA495C629C58AB4CE845F480A1AC1E5B675EF3ED0F,ignored recovery file
src/api/services/__pycache__/run_service.cpython-311.pyc,Python bytecode,8410,76F4CFEAE801C3CB4BE1522F2B808FA2CB4B7145BCB6297119970C30559D2B3D,ignored recovery file
src/api/services/event_service.py,Python source/test,10031,0B060638659044E424B7548D71FCD2DC17C3CB14F7D69BE6FEC8CB41F7A3B005,tracked modified
src/api/services/run_service.py,Python source/test,5014,33FF7E3EF4E3F4F9A0C04E97697239327E98CA1B1E657D95581214DEAA59DE3A,tracked unchanged
src/api/static/app.js,Other file,8553,A55E6E9367E7870531C464ACC0D7C09092A8189C8A03272C75F2FC452417B0A1,tracked unchanged
src/api/static/index.html,Other file,942,A004E60DB68D15FE0B498BA0885315E8A110A954187F85226812FDFB803CA10F,tracked unchanged
src/api/static/style.css,Other file,3498,CB2489563CF91E7B2432E0CDC47F6C30616389A31C1243F58178909E3F307CE5,tracked unchanged
src/ingestion/__init__.py,Python source/test,29,5661606639D07093534BA9C26290A4D4B3FE0B086397957985E0FD08E88E3659,tracked unchanged
src/ingestion/ingestor.py,Python source/test,2545,168D28B6D58AB749042F28A770DE5B914112A68D92DCC8FE488F2DF1AFF59967,tracked unchanged
src/normalization/__pycache__/mapper.cpython-311.pyc,Python bytecode,17968,3CB6876544CCAB440587090A90040D6AF4699BABF801A56E4810A09C171F60B6,ignored recovery file
src/normalization/__pycache__/mapper.cpython-312.pyc,Python bytecode,13510,94677BABCE93ADF0184FC599D8DEDDCCB6FD19E5104C43B9938E1E36BCDAE572,ignored recovery file
src/normalization/__pycache__/ocsf_validator.cpython-311.pyc,Python bytecode,21434,9F0F5A7396976CCFB1B4066D65A1C5DEADC0EB9CF750A4BE048F0156FDA5C673,ignored recovery file
src/normalization/__pycache__/ocsf_validator.cpython-312.pyc,Python bytecode,18738,03ED5506CD68AA966260CFC5A503F70FCB515A352C10981C97A05B9C92E5B0B7,ignored recovery file
src/normalization/mapper.py,Python source/test,17840,3D8AD4AF73384D180965A71C2BA9BE8CA298C0519DB63B8F955AE7E7886958A6,tracked modified
src/normalization/ocsf_validator.py,Python source/test,19043,2BD6ABF75826478809D2C88E2C369731C8841A58C3DB59C21C1C78D2B7B269CC,tracked unchanged
src/parsers/__pycache__/dsl_validator.cpython-311.pyc,Python bytecode,1174,BF4F9730845166CAAC43BF0680E0375931D734976D030F904514F7C7FD8F847B,ignored recovery file
src/parsers/__pycache__/dsl_validator.cpython-312.pyc,Python bytecode,965,CBDE7859110C2DDD98EE97B54342FF7CAAEE38EA6ECE4DF9C678F4D7F1E05B84,ignored recovery file
src/parsers/__pycache__/dsl_validator.cpython-314.pyc,Python bytecode,1115,17ADE046FD54749D3EDA95C24ADBC2B891B0245EDD3FC9FE0CF2D21A056C9726,ignored recovery file
src/parsers/__pycache__/engine.cpython-311.pyc,Python bytecode,3712,9FA5ECFF36E6503C668FCEFB6967715724664A38AB19A9C49C75EB4B7E1B5263,ignored recovery file
src/parsers/__pycache__/engine.cpython-312.pyc,Python bytecode,3220,15C25ECE1E901EA01877BD739A6572AE5258817AB47DDCCE9BA8A09F88F9581C,ignored recovery file
src/parsers/__pycache__/engine.cpython-314.pyc,Python bytecode,3712,58FDA404C52F3EDCE0D9EEADCFA9943ECE61034338266F96590D783DA11D0FF3,ignored recovery file
src/parsers/__pycache__/exceptions.cpython-311.pyc,Python bytecode,1022,8DFECC56BE223AFC83EFA6059ED11ECF17EBF3CFBD1B7FAC304BD060FF9847FF,ignored recovery file
src/parsers/__pycache__/exceptions.cpython-312.pyc,Python bytecode,863,2FB578BD34297A8DDE5F36BDFE3611E6C9F2D5FD766081D7B8AEDDBD21345F7F,ignored recovery file
src/parsers/__pycache__/exceptions.cpython-314.pyc,Python bytecode,956,8854FC89B4D2D45D714382811401B34FF768B777FC3D467074EE024E14EC2DCC,ignored recovery file
src/parsers/__pycache__/interpreter.cpython-311.pyc,Python bytecode,5207,4D9511C2657A50AC4B4EF227510B3AEC1978ECAA32AC4B2BC04C90353FA67471,ignored recovery file
src/parsers/__pycache__/interpreter.cpython-312.pyc,Python bytecode,4321,FD6A4889BA7C149622B0322EB04AC85029DDCA220B100C4D95BBE01E9716DB04,ignored recovery file
src/parsers/__pycache__/interpreter.cpython-314.pyc,Python bytecode,4627,4B353A292EAD073CA11EE71762A59AE8F280E2256B97023CAF4A604A762D4E27,ignored recovery file
src/parsers/dsl_validator.py,Python source/test,297,07EBCAF72A102196079C7279C9A5FCDCBA058C9700E3D22FFE0149C2416A536E,tracked unchanged
src/parsers/engine.py,Python source/test,2315,70B98C8206371E420AB2EDAE304CE3C23397E867A98ABAF2DE2D61C8FF592395,tracked unchanged
src/parsers/exceptions.py,Python source/test,353,BADE91E7074EC035EE38EB56A1C4D7EEBE7B210CAD2E068F0B52251DE5F16CA6,tracked unchanged
src/parsers/interpreter.py,Python source/test,3899,CB6632B9FDAEDAD2A56FB21B3752932655CD48473724B2C08E41BCBC0A602ADD,tracked unchanged
src/registry/__init__.py,Python source/test,3287,85696501BD541DA6AD6DE7820FA10B0E466B4BFEB4A901771D5E290D36645A76,tracked modified
src/registry/__pycache__/__init__.cpython-311.pyc,Python bytecode,5568,8C06D9029AD512F892E886EE7AFB112D2FE5537DDDCFCC5FE0535E9E27DD013D,ignored recovery file
src/registry/__pycache__/__init__.cpython-312.pyc,Python bytecode,2363,C42A53D07DD4501AA9C79D502E015491F1DBD4DE2AAC18D8995545706B9D9B5F,ignored recovery file
src/registry/__pycache__/__init__.cpython-314.pyc,Python bytecode,2762,07CB61FB57A0F4315BA38FAF68F183ABA055D11F0779007B6D91329DEB5F2E0C,ignored recovery file
src/vault/__init__.py,Python source/test,25,517CBBAA8A5FB6D6F525573E6EAC301A45B3795E26EE42B1114338AAF413E77A,tracked unchanged
src/vault/__pycache__/__init__.cpython-311.pyc,Python bytecode,157,4E2BDA40A5F3000822180F152A3328EE3D8C86EE167F49394626DCF861822E6D,ignored recovery file
src/vault/__pycache__/store.cpython-311.pyc,Python bytecode,4083,E179B7F4E4F30BBC61BF5FDA01EE3733883712ADDB729F526D871D2451380D80,ignored recovery file
src/vault/store.py,Python source/test,2543,5CAE5612756791347337A64BDD1F026B32D6EF32704E27F24BE5B7CF14FECEBE,tracked modified
t -q,Other file,16465,2D77F19C3AB7C748E764B5E094D289F565DE58C1994C7B17725574F51A165C8A,untracked
tests/integration/__pycache__/test_api_events.cpython-311-pytest-9.0.2.pyc,Python bytecode,27587,C0B933DC9EBC3D47570CB5FAB6608094913E4CEB55366B8FB79E0CF52F634C64,ignored recovery file
tests/integration/__pycache__/test_syslog_pipeline.cpython-311-pytest-9.0.2.pyc,Python bytecode,27264,1DBC2EB32A8D171B12737977F650A07EA1E1ED73B33DA0730B6E6A4E2BA7BA0C,ignored recovery file
tests/integration/__pycache__/test_syslog_pipeline.cpython-312-pytest-9.1.1.pyc,Python bytecode,5343,654CDF2E349697EEAF1187A169CB2BDB33728C0C4C15194135CB356AD41DC9C2,ignored recovery file
tests/integration/__pycache__/test_syslog_pipeline.cpython-314-pytest-9.1.1.pyc,Python bytecode,5767,FD3CBDF81F622F53B190E3278A32BB21DC885EC9C5D7183E394D3D6A78016C0A,ignored recovery file
tests/integration/discrepancies_report.txt,Plain text,14087,9172EE90CCBA694AA2525247D994CF72719B962CBC39EACEA9315C8A1F94E290,tracked unchanged
tests/integration/test_api_events.py,Python source/test,3588,5D1E9CFFFA1E2061D61F026494E65D7FB97519773097AE87CFC36EED569F8CE1,tracked modified
tests/integration/test_syslog_pipeline.py,Python source/test,9496,5B7991F923B0AA98CC17B593852E5D8390FCF8586D5C41985CF4304A5E34C0F9,tracked modified
tests/normalization/__pycache__/test_context_injection.cpython-311-pytest-9.0.2.pyc,Python bytecode,11669,7423CC8947D29C2E6544B2596562D709291D4F7FDEC4ACD5AF408D267DD4665D,ignored recovery file
tests/normalization/__pycache__/test_enrichment_provenance.cpython-311-pytest-9.0.2.pyc,Python bytecode,20368,6137355C1D0574A52CB9F96E09BFACAA4EBD62A0CA39B7333CE57DDCEA1DB863,ignored recovery file
tests/normalization/__pycache__/test_ocsf_validator.cpython-311-pytest-9.0.2.pyc,Python bytecode,38001,32D1BA2A343723045D441BE763CE9C27E4D100F58D0476780427B75F868CE480,ignored recovery file
tests/normalization/__pycache__/test_ocsf_validator.cpython-312-pytest-9.1.1.pyc,Python bytecode,32969,41511727BE8C678E22756C7497DEAF395557316CA55772D1C0C5805B29F98B4E,ignored recovery file
tests/normalization/__pycache__/test_pipeline_integration.cpython-311-pytest-9.0.2.pyc,Python bytecode,61378,9DC017ACF3398CF09BFAE28E7FFFBA9C71185777776157680C657498BDEDD69D,ignored recovery file
tests/normalization/__pycache__/test_pipeline_integration.cpython-312-pytest-9.1.1.pyc,Python bytecode,52028,BA2CA15A669B08EB48871DF5F13FD749BA6ED997580779A576CFD2DF46B3FB34,ignored recovery file
tests/normalization/test_context_injection.py,Python source/test,2840,B78061C2723FBAF4D0E7A90464758FD0E2D843946BBCBDB15584C8827AC86E75,untracked
tests/normalization/test_enrichment_provenance.py,Python source/test,7056,C8E5626B456D390D31A356047828AAB4F28031F702CF396D7284E663E7976577,untracked
tests/normalization/test_ocsf_validator.py,Python source/test,8785,6555E9A987BED48D433EBB4F6FB90B3AB98CC85394614D15252A31D42AF93B99,tracked unchanged
tests/normalization/test_pipeline_integration.py,Python source/test,22790,DB60D4858CEAAAFF08505E70CB6EFCC91C99A28C8184C7679C413E4BB9F0993D,tracked unchanged
tests/parsers/__pycache__/test_engine.cpython-311-pytest-9.0.2.pyc,Python bytecode,19028,B5E97F1BC554DB5A117909B3968130F35E873398285A695B36DDBEB3FFD1B50A,ignored recovery file
tests/parsers/__pycache__/test_engine.cpython-312-pytest-9.1.1.pyc,Python bytecode,16172,BA9DB13A158B50E7027A34450986D7F26D44A44BABA490AD72E39B1BD29D3236,ignored recovery file
tests/parsers/__pycache__/test_interpreter.cpython-311-pytest-9.0.2.pyc,Python bytecode,26069,D5C2489C1E20B7B92FB1BE33C8A8C1B20933B70C3C12C8ECD82CD263A85BF645,ignored recovery file
tests/parsers/__pycache__/test_interpreter.cpython-312-pytest-9.1.1.pyc,Python bytecode,22194,B824105C07BF920EB2670ACAAEB9286E74A941A647B5F321E5B166AF6AF6E3E2,ignored recovery file
tests/parsers/__pycache__/test_interpreter.cpython-314-pytest-9.1.1.pyc,Python bytecode,24849,35A938E947B0A7E300A906FA03CB25D19768FF592F56D8D091AA3727C7BBEB3E,ignored recovery file
tests/parsers/test_engine.py,Python source/test,5336,753A8FC5EA3C8ADA99168B79FD9B3052AC7A5EA3B7C091E767019D743DD385B9,tracked unchanged
tests/parsers/test_interpreter.py,Python source/test,6144,5F7C29F4DA5DB0C2B30EB2651CE26A54D24AEFBBDAC6D4EF78ED98328BFE5EE9,tracked unchanged
tests/registry/__pycache__/test_registry.cpython-311-pytest-9.0.2.pyc,Python bytecode,13437,C649A20F49D152710A599254875EADAA915F9CFA387DB10F8DD0FEA0C8640ED6,ignored recovery file
tests/registry/__pycache__/test_registry.cpython-312-pytest-9.1.1.pyc,Python bytecode,11157,EFFAB14BFFD14637679B481C4865B37AD4457F13956136A9E72F23DFB334CD0E,ignored recovery file
tests/registry/__pycache__/test_registry.cpython-314-pytest-9.1.1.pyc,Python bytecode,12209,DCC13AC1A738C2C2F609B00722474B7FF6973F078E380648D11D3EB4FA8BE19A,ignored recovery file
tests/registry/__pycache__/test_source_profile.cpython-311-pytest-9.0.2.pyc,Python bytecode,3833,52F4D747C21CADDF0DDA3B282F7898809D971698024C4E645FC9C52FDA1CDC0E,ignored recovery file
tests/registry/test_registry.py,Python source/test,3878,3DA4D0F2C0F48CA52CC57B4293387EC7045CF27E2AA874970CFED12B8B8CA75D,tracked unchanged
tests/registry/test_source_profile.py,Python source/test,1681,A1B985F8CAFAABBD23C8B17B8A4E61E38451CE5EB31F2D793E00D526AE1FADA2,untracked
ulpf/.pytest_cache/.gitignore,Git ignore file,39,E7C6BB30148CF667606DCD63E7CA77ACAA3CFB0C8303BF09E6419E1E1669DC6D,ignored recovery file
ulpf/.pytest_cache/CACHEDIR.TAG,Cache metadata,191,37DC88EF9A0ABEDDBE81053A6DD8FDFB13AFB613045EA1EB4A5C815A74A3BDE4,ignored recovery file
ulpf/.pytest_cache/README.md,Markdown documentation,310,420E808D79A6C25D3CDA0AF33BC4782314A14949866682C68CE8149E89B66B70,ignored recovery file
ulpf/.pytest_cache/v/cache/lastfailed,Other file,79,0E36A792505D4DE0C12578BE8014EF577F7B29F69C528713598C567C82517ADA,ignored recovery file
ulpf/.pytest_cache/v/cache/nodeids,Other file,73,BFC4427B5A4F22794815D07B3BA4DCF43A676BCEF91D7F1BB836FE5A6F28EE2A,ignored recovery file
ulpf/docs/decisions/approved-decision-record.md,Markdown documentation,23057,F48C99EF23A903368CCA83EC3EACEA7321CF5F7353EA15901DBFF07F812A82F4,untracked
ulpf/docs/decisions/decision-selection-worksheet.md,Markdown documentation,8687,7B47C3049629CE55BB3ED21120A1795B6D59BEFA184B3A93FCE6F2D448EB0EB3,untracked
ulpf/docs/decisions/implementation-roadmap.md,Markdown documentation,34383,F54A9CA905B16FF00EBEB07625F8E92C5E75EDFA053F17748D06931A5BB19A01,untracked
worktree-provenance-audit.md,Markdown documentation,13412,76D0C5DB782FF7BC8E3B9700328C0E2153375244044180D022C367375EA9A084,untracked
```

## Snapshot boundary

This manifest records the mixed worktree exactly as preserved. It does not authorize cleanup, Git mutations, implementation separation, commits, or Phase 2 work.
