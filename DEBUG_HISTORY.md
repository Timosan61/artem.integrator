# Debug History - Artyom Integrator

## 2025-07-25 - Railway Healthcheck 8 Webhook ?@>1;5<K

### ?8A0=85 >H81:8
Railway 45?;>9 =5 ?@>E>48B healthcheck 8 ?@8;>65=85 =54>ABC?=>. Endpoint 2>72@0I05B 404 "Application not found".

### !8<?B><K
- Railway healthcheck timeout G5@57 2 ?>?KB:8
- https://web-production-84d8.up.railway.app/ 2>72@0I05B 404
- >38 A1>@:8 =54>ABC?=K G5@57 Railway CLI
- @8;>65=85 =5 AB0@BC5B ?>A;5 45?;>O

### >?KB:8 8A?@02;5=8O

#### >?KB:0 1: #?@>I5=85 healthcheck endpoint
**@>1;5<0**: !;>6=0O ;>38:0 2 /health endpoint <>3;0 2K7K20BL >H81:8 ?@8 8=8F80;870F88
**59AB285**: !>740= C?@>IQ==K9 /health endpoint B>;L:> A ?@>25@:>9 Telegram 1>B0
** 57C;LB0B**: L @8;>65=85 2AQ 5IQ =54>ABC?=>

#### >?KB:0 2: A?@02;5=85 ;>38:8 :>=D83C@0F88 webhook
**@>1;5<0**: 5@5<5==0O WEBHOOK_URL =5 8A?>;L7>20;0AL, GB> <>3;> ?@82>48BL : =5:>@@5:B=>9 CAB0=>2:5 webhook
**59AB285**: 
- >102;5=0 ?>445@6:0 ?5@5<5==>9 WEBHOOK_URL A 872;5G5=85< base_url
- #;CGH5=0 ?@8>@8B5B=>ABL: WEBHOOK_URL ’ BASE_URL ’ RAILWAY_PUBLIC_DOMAIN
- >102;5=> 45B0;L=>5 ;>38@>20=85 ?@>F5AA0 CAB0=>2:8 webhook
- >102;5=0 20;840F8O URL 8 4803=>AB8G5A:89 endpoint /debug/webhook-config
** 57C;LB0B**: L 5?;>9 2AQ 5IQ =5 @01>B05B

### "5:CI0O 38?>B570
@>1;5<0 <>65B 1KBL 2:
1. **Dockerfile 8;8 A1>@:5** - >H81:8 ?@8 :>?8@>20=88 D09;>2 8;8 CAB0=>2:5 7028A8<>AB59
2. **5@5<5==K5 >:@C65=8O Railway** - >BACBAB2CNB =5>1E>48<K5 ?5@5<5==K5 4;O @01>BK ?@8;>65=8O
3. **Startup ?@>F5AA** - >H81:8 ?@8 8=8F80;870F88 A5@28A>2 (MCP, Voice, Agent)
4. **Port mapping** - ?@8;>65=85 A;CH05B =5?@028;L=K9 ?>@B

### !;54CNI85 H038
1. @>25@8BL Railway deployment logs G5@57 251-8=B5@D59A
2. @>25@8BL 2A5 ?5@5<5==K5 >:@C65=8O 2 Railway dashboard
3. @5<5==> C?@>AB8BL startup ?@>F5AA, C1@02 A;>6=K5 8=8F80;870F88
4. >1028BL ?@>AB>9 "hello world" endpoint 4;O 4803=>AB8:8

### 06=K5 C@>:8
1. Railway CLI =5 2A5340 ?@54>AB02;O5B 45B0;L=K5 ;>38 - =C6=> 8A?>;L7>20BL 251-8=B5@D59A
2. @8 ?@>1;5<0E A 45?;>5< =C6=> C?@>I0BL ?@8;>65=85 4> <8=8<C<0
3. Healthcheck 4>;65= 1KBL <0:A8<0;L=> ?@>ABK< 8 =5 7028A5BL >B 2=5H=8E A5@28A>2