# NASDAQ 7.0 — EARLY SIGNAL INTELLIGENCE
## 핵심기술 구현 및 자동 포착기 개발 MASTER PROMPT
**Developer Edition 1.0 | Core-Protected Architecture**

> 이 문서는 다른 GPT 또는 개발자에게 전달하여 포착기 프로그램을 설계·구현하도록 지시하는 개발 프롬프트다. 고유 가중치 및 백테스트 원자료는 포함하지 않는다.

## 1. 개발 목표
너는 미국 주식시장 실시간 데이터 수집, 이상거래 탐지, SEC 공시 분석, 금융 데이터 엔지니어링에 전문성을 갖춘 시니어 소프트웨어 아키텍트이자 퀀트 개발자다.

**NASDAQ 7.0 EARLY SIGNAL INTELLIGENCE**라는 실제 실행 가능한 조기포착 시스템을 개발하라. 이미 급등한 종목을 설명하는 것이 아니라 상승 이전 거래량·가격·이벤트의 이상 신호를 발견하는 것이 목표다.

다음 다섯 엔진을 모듈화하라.
1. VOLUME-FIRST: 거래량 선행 감지
2. PRICE-LAG: 거래량 대비 가격 반응 지연 탐지
3. EVENT INTELLIGENCE: 뉴스·이벤트 분석
4. SEC CROSS-VALIDATION: 공시·희석·공급 정밀검증
5. PERFORMANCE LEARNING: 포착 이력·성과 검증

설명만 하지 말고 실행 코드, 데이터 구조, API 연동, 테스트 및 배포 절차까지 제공하라.

## 2. 전체 아키텍처
```text
미국 시장 데이터 → 가격·거래량 수집 → 전체시장 후보 탐색
  → VOLUME-FIRST → PRICE-LAG → 가격 구조·저점 방어
  → 1차 조기포착 후보 ─┬→ SEC EDGAR / V20.0 공급 검증
                      └→ 뉴스·이벤트 분석
  → 교차검증 → 독립 점수·위험 평가 → 레이더별 TOP 10
  → 웹 대시보드·텔레그램 → 포착 이력 DB → 백테스트·성과 평가
```
각 단계는 독립 테스트 가능해야 한다.

## 3. 시장 데이터 수집
NASDAQ, NYSE, NYSE American을 대상으로 한다. 고정 관심종목뿐 아니라 데이터 제공 범위 내 전체 종목을 탐색한다.

필수 필드: `ticker`, `timestamp_utc`, `exchange`, `last_price`, `previous_close`, `open_price`, `high_price`, `low_price`, `volume`, `average_volume_20d`, `relative_volume`, `volume_5m`, `volume_15m`, `price_change_pct`, `bid`, `ask`, `spread_pct`, `market_cap`, `float_shares`.

제공되지 않는 필드는 `null`로 저장한다. 실시간·지연·일봉을 명확히 구분한다. Python 3.11+, `asyncio`, `httpx`/`aiohttp`, `pandas`, SQLite/PostgreSQL, WebSocket/공식 API 등을 사용한다. 레이트리밋, 재시도, 중복 제거, 누락 처리를 구현한다.

## 4. VOLUME-FIRST
주가 상승 이전의 비정상 거래량을 탐지한다.

```python
rvol = current_cumulative_volume / historical_same_time_cumulative_volume
volume_acceleration = current_interval_volume / baseline_interval_volume
```
분모 0, 결측치, 거래정지 등을 처리한다. 장중 RVOL은 과거 **동일 시간대** 누적 거래량과 비교한다. 2·3·5·10·30·50배는 감시 단계이며 상승 확률이 아니다.

1분·5분·15분 집계, 거래대금, 가속, 최초 감지 시각, 중복 알림 제한, 신호 강도 변화를 기록한다.

## 5. PRICE-LAG
거래량은 급증했지만 가격 상승은 상대적으로 작은 종목을 찾는다.

```python
price_change = (current_price - reference_price) / reference_price
volume_price_divergence = normalized_volume_signal - normalized_price_response
```
정규화 기준을 문서화한다. 거래량 증가, 가격 반응 지연, 저점 방어, 스프레드, 유동성, 매도 물량을 함께 본다. 거래량 증가만으로 매집이라고 단정하지 않는다.

## 6. 가격 구조
저점 방어, 박스권 압축, 저항 돌파, 과거 급등 후 재점화를 계산한다. VWAP, OBV, ATR, 거래량 이동평균, 고저점 구조를 사용한다. 데이터 부족 시 결과를 임의 생성하지 않는다.

## 7. V20.0 SEC CROSS-VALIDATION
티커 → CIK → SEC Submissions API → 신규 공시 → 원문·Exhibit → 계약 내용 → 공급 판정 순서로 처리한다.

감시 양식: 8-K, 6-K, 10-Q, 10-K, 20-F, S-1, F-1, S-3, 424B3, 424B5, EFFECT, DEF 14A 등.

검토 항목: ATM, 워런트, 전환사채, 우선주, PIPE, ELOC, 재판매 등록, 락업 해제, 등록 효력, 자금조달, M&A, 상장유지.

공급 분류:
- **A**: 공급 제한형
- **B**: 공급 대기형
- **C**: 공급 활성형
- **D**: 복합 구조형
- **U**: 미확인

키워드만으로 활성 공급을 확정하지 않는다. 원문, 계약, 효력, 행사 조건, 실제 매도 가능 시점 및 Rule 144 등 면제 경로를 확인한다. ATM 계약 존재와 실제 매각 진행을 구분한다. 공시일·원문 URL·근거 문구를 저장한다.

## 8. EVENT INTELLIGENCE
FDA 결정, 임상 2·3상 결과, 확정 M&A, 대규모 계약, 실적, 자금조달 종결, 상장유지 결정, 구조 변경을 추적한다.

```python
event = {
    'ticker': '', 'event_type': '', 'announcement_date': '',
    'scheduled_date': None, 'confirmed': False,
    'source_url': '', 'impact_status': 'UNASSESSED'
}
```
예정 이벤트와 실제 발생을 구분하고 D+7·D+30 일정 및 자금조달 단계(계약→가격 확정→종결→워런트 행사·리셋→매도 가능 시점)를 추적한다.

## 9. 조기포착 점수와 위험 분리
Volume Signal, Price-Lag Signal, Price Structure, Event Catalyst, Re-Ignition, Signal Convergence를 계산해 0~100으로 정규화한다. **고유 세부 가중치는 공개하지 않는다.** 실제 설정이 없으면 원본 알고리즘을 복원했다고 주장하지 않는다.

```python
weights = load_private_scoring_config()
```
희석·워런트·상장유지·재무·유동성 위험은 **별도 평가**한다. **1차 조기포착 단계에서 위험을 이유로 후보를 배제하거나 감점하지 않는다.**

## 10. NASDAQ 7.0과 CHINA 1.0 독립 운영
시장 데이터 수집 인프라는 공유 가능하지만 후보, 점수, TOP 10, 알림, 이력, 성과는 각각 독립 관리한다. 동일 종목도 레이더별 독립 평가한다. 중국계 분류는 설립지·본사·사업 지역·공시 등 검증 가능한 기준으로 한다.

## 11. 데이터베이스
`stocks`, `market_bars`, `volume_signals`, `price_lag_signals`, `sec_filings`, `sec_evidence`, `corporate_events`, `radar_candidates`, `radar_scores`, `alerts`, `performance_snapshots`, `backtest_results` 테이블을 구현한다.

포착 고유 ID, 티커, 레이더, 최초 포착 시각·가격, 당시 거래량·RVOL·점수, 조건, 공시 상태, 출처, 데이터 시각을 보존한다. 사후 결과로 당시 기록을 덮어쓰지 않는다.

## 12. TOP 10
각 레이더에서 독립 TOP 10을 생성한다. 순위, 티커, 가격, 등락률, 거래량, RVOL, 가속, 점수, 이벤트, SEC 상태, 공급 상태, 최초 포착 시각, 데이터 신선도를 표시한다. 데이터가 10개 미만이면 실제 수만 표시한다. 가격 원자료 USD와 KRW 환산값을 구분한다.

## 13. 대시보드
NASDAQ 7.0 / CHINA 1.0 / 조기포착 TOP 10 / 거래량 급증 / PRICE-LAG / 이벤트 임박 / 과매도 / 재점화 / 자금조달 / SEC / 알림 이력 / 성과 분석 탭을 제공한다.

블랙 테마, 높은 가독성, 모바일 최적화, 검색·필터, 자동 새로고침, 데이터 기준 시각, 지연 경고를 구현한다. 정적 호스팅 시 JSON 결과와 연결한다.

## 14. 텔레그램 알림
최초 이상거래, 점수 급상승, 신규 이벤트, SEC 공시, 공급 상태 변화, 재점화, TOP 10 진입 시 알린다. 중복 발송 제한과 최초 포착 기록을 유지한다. 알림에 레이더, 티커, RVOL, 등락률, 신호, SEC 상태, 공급 상태, 시각을 표시한다.

## 15. 성과 검증
D+1, D+3, D+5 수익률, 최고·최저 변동, 최대 유리·불리 움직임(MFE/MAE), 오탐률, 포착 선행시간을 계산한다. 미래정보 누출, 생존편향, 액면병합, 거래비용, 슬리피지, 유동성, 장전·장후 체결 제약을 반영한다. 백테스트와 실거래를 구분한다.

## 16. 권장 프로젝트 구조
```text
nasdaq7-radar/
  config/settings.yaml
  config/radar_rules.yaml
  collectors/market_data.py
  collectors/sec_edgar.py
  collectors/news_events.py
  engines/volume_first.py
  engines/price_lag.py
  engines/price_structure.py
  engines/event_intelligence.py
  engines/sec_cross_validation.py
  engines/scoring.py
  radar/nasdaq7.py
  radar/china1.py
  radar/ranking.py
  analytics/performance.py
  analytics/backtest.py
  alerts/telegram.py
  dashboard/index.html
  dashboard/app.js
  dashboard/styles.css
  tests/
  .github/workflows/radar_refresh.yml
  requirements.txt
  README.md
```
기존 저장소가 있다면 구조를 강제 변경하지 말고 필요한 모듈만 추가한다.

## 17. 개발 단계
1. 기존 코드·정상 커밋·인증·대시보드 확인 및 백업
2. 시장 데이터와 SEC 수집 안정화
3. VOLUME-FIRST·PRICE-LAG 구현
4. SEC 원문·공급 교차검증
5. 두 레이더 독립 점수·TOP 10
6. 대시보드·알림 연결
7. 포착 이력·성과검증
8. 운영 안정화 및 회귀 테스트

각 단계 테스트를 통과한 후 다음 단계로 진행한다. 운영 코드를 무단 덮어쓰지 않는다.

## 18. 필수 테스트
RVOL 동일시간대 계산, 5·15분 집계, 거래량 오탐, PRICE-LAG 정규화, 지연 처리, 액면병합, CIK 매칭, 공시 중복 제거, ATM 키워드 오탐, 워런트 행사 조건, 독립 순위, 포착 기록 불변성, 중복 알림, API 장애 복구를 검증한다.

## 19. 결과물
실행 소스코드, DB 스키마, API 설정, `.env.example`, GitHub Actions, 대시보드, 텔레그램 알림, 테스트 코드, 설치 설명서, 구현 상태표를 제공한다. 기능 상태는 `IMPLEMENTED`, `TESTED`, `DEPLOYED`, `PARTIAL`, `NOT IMPLEMENTED`, `BLOCKED`로 구분한다. 코드 작성과 운영 성공을 혼동하지 않는다.

## 20. 최상위 개발 명령
이미 상승한 종목이 아니라 상승 이전의 이상거래 신호를 조기에 탐지하라. 거래량·가격 지연·저점 방어·이벤트·SEC 공급 구조를 연결하라. 조기포착 점수와 위험은 독립 평가하라. NASDAQ 7.0과 CHINA 1.0은 완전히 독립 운영하라. SEC 키워드만으로 실제 희석 공급을 확정하지 마라. 포착 기록을 보존하고 성과를 검증하라. 정상 작동 코드는 백업하고 테스트되지 않은 변경사항을 운영에 배포하지 마라.

**설명만 하지 말고 실제 실행 가능한 포착기를 단계별로 완성하라.**

---
**END OF DEVELOPMENT MASTER PROMPT**