# Chroma 로컬 운영

외부 서버/클라우드로 전송하지 않는다. 같은 서버에서 실행 설정, 데이터, 최근 7개
백업을 관리한다. 컨테이너 재생성·잘못된 데이터 변경에 대비하며, 서버/디스크 전체
손실까지 보호하지는 않는다. 백업 도구는 Python 3.12 이상, Docker CLI, Linux를 사용한다.

## 기존 컨테이너에 백업부터 적용

현재 컨테이너 `epic_mclaren`을 그대로 사용할 수 있다. 저장 경로는 Docker inspect로
확인한 `/data` bind mount에서 자동으로 얻는다. 백업은 잠시 서비스를 중지한다.
한 데이터 폴더를 다른 Chroma 컨테이너나 프로세스가 동시에 쓰지 않아야 한다.

저장소 루트에서 Docker 호스트에 아래 파일을 설치한다. 이 명령은 **해당 서버에서**
실행해야 하며, 저장소에 파일을 추가하는 것만으로 원격 설정이 바뀌지는 않는다.

```bash
sudo install -d -m 755 /opt/certificate-ops
sudo install -m 755 backend/scripts/chroma_local_backup.py /opt/certificate-ops/
sudo install -m 600 infra/chroma/backup.env.example /etc/chroma-local-backup.env
sudo install -m 644 infra/chroma/chroma-local-backup.service /etc/systemd/system/
sudo install -m 644 infra/chroma/chroma-local-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start chroma-local-backup.service
sudo journalctl -u chroma-local-backup.service -n 30 --no-pager
```

첫 백업 성공을 확인한 뒤 자동 실행을 켠다.

```bash
sudo systemctl enable --now chroma-local-backup.timer
systemctl list-timers chroma-local-backup.timer
```

서버 시간 기준 매일 04:00에 실행한다. 꺼져 있어 놓친 실행은 부팅 후 실행된다.
`/etc/chroma-local-backup.env`에서 대상 컨테이너, 백업 위치, 보관 개수를 변경한다.
수동 백업도 같은 도구를 사용한다.

```bash
sudo python3 /opt/certificate-ops/chroma_local_backup.py backup \
  --container epic_mclaren --backup-dir /data01/chroma-backups --keep 7
```

동작: 중복 실행 잠금 → 정상 중지 → 전체 데이터 압축 → 원래 실행 중이었으면 재시작
→ SHA256/압축파일 검사 → 완성된 백업으로 확정 → 오래된 백업 정리.
실패한 백업으로 기존 백업을 교체하지 않는다. 중지/압축 중 일반 오류가 나도 재시작을
시도하며 재시작 오류는 실패로 보고한다. 호스트 종료나 SIGKILL은 finally를 실행할 수
없으므로 다음 부팅에 서비스 실행 상태를 확인해야 한다. 이미 중지된 서비스는 켜지 않는다.
백업은 이미지 ID/참조, 데이터 경로와 시각도 기록한다. 환경 변수/인증 정보는 저장하지 않는다.
권한 0700 백업 디렉터리 아래 완성본만 보관하며 다른 파일은 정리하지 않는다.

## 복원

예시의 SNAPSHOT은 실제 `snapshot-날짜-식별자` 디렉터리로 바꾼다.

```bash
sudo python3 /opt/certificate-ops/chroma_local_backup.py verify \
  /data01/chroma-backups/SNAPSHOT
sudo python3 /opt/certificate-ops/chroma_local_backup.py restore \
  /data01/chroma-backups/SNAPSHOT --target /data01/chroma-restored
```

복원 대상은 **존재하지 않는 새 폴더**여야 한다. 현재 데이터는 덮어쓰지 않고 서비스도
자동 전환하지 않는다. 백업 시점과 같은 이미지로 별도 포트에서 실행해 컬렉션·건수·검색을
확인한 뒤 전환한다. 복원 파일 소유자는 복원 실행 사용자이므로, 컨테이너 실행 UID가
root가 아니면 해당 UID가 폴더를 읽고 쓸 수 있도록 권한을 조정한다.
파일 검사는 실행 가능한 DB 검증을 대체하지 않는다. 월 1회 실제 복원을 시험한다.

## Compose로 실행 관리 전환

기존 데이터가 완전히 없다고 단정하지 않는다. 기존 컨테이너를 삭제하거나 폴더를
초기화하지 않고, 위 백업을 만든 뒤 설정만 통일한다.

1. `infra/chroma/.env.example`을 같은 폴더의 `.env`로 복사한다.
2. 기존 이미지 ID는 `docker inspect epic_mclaren --format '{{.Image}}'`로 확인한다.
   그 ID에 `docker image inspect IMAGE_ID --format '{{json .RepoDigests}}'`를 실행해
   검증된 `chromadb/chroma@sha256:...` 값을 CHROMA_IMAGE에 넣는다. latest를 쓰지 않는다.
   digest가 없으면 임의의 최신 이미지를 받지 말고 기존 이미지의 보존/버전 확인을 먼저 한다.
3. CHROMA_DATA_DIR은 `/data01/chroma-data`처럼 실제 존재하는 절대 경로를 지정한다.
   현재 이미지가 `/data`를 사용하는지 시작 로그도 확인한다. 폴더가 없으면 Compose가
   빈 폴더를 자동 생성하는 대신 실패한다.
4. 기본 포트는 localhost의 38000이다. API가 다른 서버에 있으면 접근 가능한 서버의
   사설 IP를 CHROMA_BIND_IP에 지정한다.
5. 기존 서비스의 백업과 점검이 끝나면 다음으로 전환한다. 같은 폴더에 두 서버를 동시에
   실행하지 않는다. Compose 실행 실패 시 먼저 Compose 서비스를 멈춘 뒤 기존 것을 시작한다.

```bash
docker stop epic_mclaren
cd infra/chroma
docker compose --project-name certificate-chroma up -d
docker compose --project-name certificate-chroma ps
curl -f -i --max-time 5 http://127.0.0.1:38000/api/v2/heartbeat
```

사설 IP에 바인딩했다면 heartbeat 주소도 그 IP로 바꾼다. 이후에는 같은 폴더에서
`docker compose --project-name certificate-chroma restart chroma`로 재시작한다.
백업 설정의 CHROMA_CONTAINER도 `docker compose --project-name certificate-chroma ps`
에 표시된 새 컨테이너 이름으로 갱신한다. 자동 재시작은 수동 중지를 되돌리지 않는다.

MariaDB 원본 백업/재색인 계획은 별도다. 이 도구가 MariaDB까지 백업하지는 않는다.
Chroma 로컬 백업을 잃으면 원본과 동일 모델/문서 버전으로 색인을 다시 생성해야 한다.

근거: [Chroma 저장 경로](https://docs.trychroma.com/guides/deploy/docker),
[정지 후 파일 백업](https://cookbook.chromadb.dev/strategies/backup/).
