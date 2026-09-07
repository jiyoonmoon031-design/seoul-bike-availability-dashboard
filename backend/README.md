# Backend

광진구·성동구 따릉이 대여소의 기본정보 및 실시간 자전거 현황을
수집·저장하기 위한 Spring Boot 백엔드이다.

## 1. 개발 환경

- Java 21
- Spring Boot
- Gradle
- MySQL

## 2. 환경변수 설정

백엔드 실행을 위해 다음 환경변수가 필요하다.

| 환경변수                  | 설명                           |
| ------------------------- | ------------------------------ |
| `DATABASE_URL`            | MySQL 데이터베이스 연결 URL    |
| `DB_USERNAME`             | MySQL 사용자명                 |
| `DB_PASSWORD`             | MySQL 비밀번호                 |
| `SEOUL_OPEN_DATA_API_KEY` | 서울 열린데이터광장 API 인증키 |

환경변수 이름은 저장소의 `.env.example`을 참고한다.

실제 API Key 및 데이터베이스 비밀번호는 Git에 커밋하지 않는다.

예시:

```text
DATABASE_URL=jdbc:mysql://localhost:3306/ddareungi
DB_USERNAME=<your-db-username>
DB_PASSWORD=<your-db-password>
SEOUL_OPEN_DATA_API_KEY=<your-api-key>
```

## 3. Backend 실행

MySQL을 실행하고 필요한 환경변수를 설정한 뒤,
`backend` 디렉터리에서 Spring Boot 애플리케이션을 실행한다.

Windows:

```bash
gradlew.bat bootRun
```

Linux/macOS:

```bash
./gradlew bootRun
```

## 4. 실행 후 동작

백엔드 실행 시 `station` 테이블이 비어 있는 경우
광진구·성동구 대상 대여소 기본정보 초기화를 시도한다.

실시간 따릉이 현황은 5분 주기로 수집하여
`station_snapshot` 테이블에 저장한다.

대여소 기본정보는 설정된 스케줄에 따라 주기적으로 갱신한다.

## 5. 테스트 실행

`backend` 디렉터리에서 다음 명령으로 테스트를 실행한다.

Windows:

```bash
gradlew.bat test
```

Linux/macOS:

```bash
./gradlew test
```
