# 검증 결과

검증일: 2026-09-16. 실행 환경: Linux, Python 3.13.5.

**총 49개 회귀 테스트 통과, 실패 0개.** 각 그룹을 별도 실행했고, 빠짐·중복 없이 49개 테스트 이름을 대조했다. 개별 테스트는 매번 새로운 임시 홈/임시 소스 복사본에서 수행한다. 사용자 실제 홈·Gitea·모델 계정은 사용하지 않았다.

## 재현

```bash
python3 -m unittest discover -s tests -v
./agentctl verify
bash -n agentctl install.sh
```

이번 실행은 도구 호출 시간 제한 때문에 `python -m unittest discover -s tests -v -k test_0`부터 `test_4`까지 5개 그룹으로 나누었다. unittest가 보고한 그룹 실행시간 합은 56.526초다. 실제 전체 작업시간이나 사용자 기기에서의 예상시간을 뜻하지 않는다.

## 주요 검사 범위

| 범위 | 결과 |
|---|---|
| conf의 메인·8개 역할 모델/추론 유지 | 통과 |
| TOML·명명·스킬 metadata·lock·미지원 공통 키 | 통과 |
| 기본 미리보기의 대상 홈 미생성 | 통과 |
| 인증·세션·시스템 스킬·미등록 사용자 항목 보존 | 통과 |
| 반복 설치, 관리 스킬 제거, 원본 상태 복원 | 통과 |
| 옛 전체 agents 링크/파일 링크 분리·복원 | 통과 |
| 저장소 이동·삭제·수정 후 콘텐츠 복구 | 통과 |
| 알려진 옛 tester/스킬 이전, 알 수 없는 중복 중단 | 통과 |
| 전역 override·설치본 직접 변경·모델 정책 변경 차단 | 통과 |
| 앱이 쓴 trust/UI 보존, 기기별 예외 분리 | 통과 |
| 백업 위변조, 경로 이탈, 상위 심볼릭 링크 방어 | 통과 |
| 실패 주입 후 파일 복원, 미완료 journal 복구 | 통과 |
| 모델 호출 없는 CLI 검사 성공/실패 분기 | 테스트용 가짜 CLI로 통과 |
| mac/ubuntu/windows 설정 분기 | Linux에서 분기 로직만 통과 |
| 작업 기록 Markdown 선택 복사·충돌 방어 | 통과 |
| 별도 프로필, 하위 agents.enabled=false 생성 | 통과 |
| 소스와 설치본 버전 차이 감지 | 통과 |

## 미검증 범위

이 컨테이너에는 실제 Codex 바이너리가 없다. 실사용 모델 호출, Luna/max 지원, 계정별 Astra/Terra/Luna/Sol 사용 가능 여부, 실제 sandbox 집행, GUI/IDE 세션 동작은 검증하지 않았다. macOS·Windows 네이티브 OS, Keychain, Windows ACL/PowerShell 실행도 미검증이다. Python 3.11을 최소 요구하지만 실제 테스트 인터프리터는 3.13.5다.

실제 Gitea 인증·push/pull, 모든 프로젝트의 로컬 override, 프롬프트 사용량/비용/품질 개선은 측정하지 않았다. 테스트 통과를 전체 사용자 환경의 정상 동작 보증으로 해석하지 않는다.

## 검증한 코드 식별자

- scripts/agentctl.py SHA256: `0ff1183acb39cae43a20ccf5897d5f2bb2bbf2a77237417302eac697cea440e7`
- tests/test_agentctl.py SHA256: `0fb2dc67d058083a5d8e2bf59c82e65ab495062da700c00edb2185e558518737`
- 개별 전체 결과: [test-output.txt](test-output.txt)

## 실제 통과 테스트

- `test_01_original_model_policy_and_role_names_preserved`
- `test_02_unknown_shared_key_rejected`
- `test_03_malformed_toml_rejected_before_install`
- `test_04_skill_hash_requires_review_and_relock`
- `test_05_malformed_yaml_rejected`
- `test_06_default_install_is_read_only_preview`
- `test_07_install_uninstall_preserve_private_and_unmanaged`
- `test_08_repeated_install_is_idempotent`
- `test_09_legacy_whole_agent_link_detached_and_restored`
- `test_10_legacy_skills_migrate_once_without_resurrection`
- `test_11_legacy_tester_known_only`
- `test_12_unknown_legacy_tester_fails_closed`
- `test_13_unknown_legacy_skill_fails_closed`
- `test_14_existing_canonical_skill_is_backed_up`
- `test_15_duplicate_name_in_different_skill_folder_rejected`
- `test_16_duplicate_custom_agent_name_rejected`
- `test_17_global_override_is_not_deleted`
- `test_18_source_edit_does_not_change_active_install`
- `test_19_direct_managed_edit_is_never_overwritten`
- `test_20_app_written_trust_and_ui_are_captured`
- `test_21_explicit_machine_edits_are_applied`
- `test_22_machine_cannot_change_model_policy`
- `test_23_shared_runtime_model_change_is_not_silently_adopted`
- `test_24_removed_skill_restores_baseline_and_releases_ownership`
- `test_25_backup_tampering_stops_uninstall`
- `test_26_source_link_rejected`
- `test_27_legacy_whole_skills_link_fails_before_writes`
- `test_28_state_target_escape_rejected`
- `test_29_home_itself_and_repo_roots_rejected`
- `test_30_repo_relocation_does_not_break_install`
- `test_31_state_import_copies_only_markdown_without_overwrite`
- `test_32_state_import_symlink_parent_rejected`
- `test_33_os_layers_do_not_force_auth_or_change_models`
- `test_34_existing_credentials_store_and_trust_preserved_locally`
- `test_35_failed_cli_preflight_leaves_original_files`
- `test_36_successful_cli_preflight_uses_config_only_command`
- `test_37_fault_injection_restores_prior_files`
- `test_38_incomplete_journal_recovers`
- `test_39_uninstall_does_not_depend_on_new_broken_source`
- `test_40_profiles_are_explicit_separate_files`
- `test_41_recursive_agents_disabled_in_rendered_config`
- `test_42_toml_round_trip_nested_arrays_inline_tables_and_keys`
- `test_43_manager_symlink_rejected`
- `test_44_root_state_and_system_copies_not_in_runtime_sources`
- `test_45_removed_old_repo_restores_saved_content_not_broken_links`
- `test_46_changed_relative_link_target_not_overwritten_on_rollback`
- `test_47_tampered_resolved_backup_blocks_all_restore_writes`
- `test_48_tampered_retired_skill_baseline_blocks_sync`
- `test_49_doctor_flags_source_install_version_difference`
