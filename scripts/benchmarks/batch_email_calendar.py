import time
from common import benchmark_call, save_batch_results
from services.email.service import create_email_draft, send_email_with_approval
from services.email.draft import update_draft
from services.email.approval import validate_approval
from services.email.provider import MockEmailProvider
from services.calendar.service import prepare_calendar_event, create_calendar_event_with_approval
from services.calendar.event import update_calendar_event_draft
from services.calendar.approval import validate_calendar_approval
from services.calendar.provider import MockCalendarProvider



def run_batch_email_calendar():
    print("\n🚀 [BATCH C] Running Email & Calendar Controlled Pipeline Benchmarks...")
    results = []

    # 1. Email Draft Creation
    def test_email_draft():
        return create_email_draft("recruiter@tech.co", "Senior SDE Application", "Cover letter text.")

    results.append(benchmark_call(
        name="Email: Draft Creation + SHA-256 Hash + Approval Token",
        category="Email",
        mode="LOCAL_REAL",
        fn=test_email_draft,
        iterations=50,
    ))

    # 2. Email Draft Mutation
    sample_email = test_email_draft()
    draft_id = sample_email["draft"]["draft_id"]

    def test_email_update():
        return update_draft(draft_id, new_body=f"Updated body {time.perf_counter()}")

    results.append(benchmark_call(
        name="Email: Draft Mutation + Version Bump + Re-hash",
        category="Email",
        mode="LOCAL_REAL",
        fn=test_email_update,
        iterations=50,
    ))

    # 3. Email Approval Validation
    sample_for_val = test_email_draft()
    d_id = sample_for_val["draft"]["draft_id"]
    a_id = sample_for_val["approval_token"]["approval_id"]

    def test_email_val():
        return validate_approval(a_id, d_id, session_user="Prem")

    results.append(benchmark_call(
        name="Email: Approval Token Validation (10 Security Checks)",
        category="Email",
        mode="LOCAL_REAL",
        fn=test_email_val,
        iterations=50,
    ))

    # 4. Email Full Controlled Send
    email_prov = MockEmailProvider()

    def test_email_send():
        d = create_email_draft("team@innovate.org", "Job Inquiry", "Profile overview.")
        return send_email_with_approval(
            approval_id=d["approval_token"]["approval_id"],
            draft_id=d["draft"]["draft_id"],
            user_confirmation_text="Yes, send it",
            provider=email_prov,
        )

    results.append(benchmark_call(
        name="Email: Full Pipeline (Draft -> Validate -> Send -> Verify -> Audit)",
        category="Email",
        mode="LOCAL_REAL",
        fn=test_email_send,
        iterations=40,
    ))

    # 5. Calendar Event Draft Creation
    def test_cal_draft():
        return prepare_calendar_event("Architecture Sync", "2026-09-20T10:00:00", "2026-09-20T11:00:00", "UTC")

    results.append(benchmark_call(
        name="Calendar: Draft Creation + Hash + Approval Token",
        category="Calendar",
        mode="LOCAL_REAL",
        fn=test_cal_draft,
        iterations=50,
    ))

    # 6. Calendar Event Mutation
    sample_cal = test_cal_draft()
    ev_id = sample_cal["event_draft"]["event_id"]

    def test_cal_update():
        return update_calendar_event_draft(ev_id, new_title=f"Sync {time.perf_counter()}")

    results.append(benchmark_call(
        name="Calendar: Event Mutation + Version Bump + Re-hash",
        category="Calendar",
        mode="LOCAL_REAL",
        fn=test_cal_update,
        iterations=50,
    ))

    # 7. Calendar Approval Validation
    sample_cal_val = test_cal_draft()
    c_ev_id = sample_cal_val["event_draft"]["event_id"]
    c_a_id = sample_cal_val["approval_token"]["approval_id"]

    def test_cal_val():
        return validate_calendar_approval(c_a_id, c_ev_id, session_user="Prem")

    results.append(benchmark_call(
        name="Calendar: Approval Token Validation (Security Checks)",
        category="Calendar",
        mode="LOCAL_REAL",
        fn=test_cal_val,
        iterations=50,
    ))

    # 8. Calendar Full Controlled Create
    cal_prov = MockCalendarProvider()

    def test_cal_create():
        ev = prepare_calendar_event("Executive Review", "2026-09-22T14:00:00", "2026-09-22T15:00:00", "UTC")
        return create_calendar_event_with_approval(
            approval_id=ev["approval_token"]["approval_id"],
            event_id=ev["event_draft"]["event_id"],
            user_confirmation_text="Yes, create it.",
            provider=cal_prov,
        )

    results.append(benchmark_call(
        name="Calendar: Full Pipeline (Draft -> Validate -> Create -> Verify -> Audit)",
        category="Calendar",
        mode="LOCAL_REAL",
        fn=test_cal_create,
        iterations=40,
    ))

    save_batch_results("batch_email_calendar", results)


if __name__ == "__main__":
    run_batch_email_calendar()
