#!/usr/bin/env python3
"""
End-to-end happy path for the Keystone PoC, driven purely through the HTTP API.

    pip install requests
    python e2e_demo.py

Flow: course -> 4 kinds of users -> team -> 3 projects -> team applies to two of them ->
supervisor accepts one -> team agrees (the other application is auto-withdrawn) ->
team submits -> instructor approves -> print the final state from every role's view.

Safe to re-run: every email, course code and name gets a random suffix.
"""
# ruff: noqa

import random
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8000"
PASSWORD = "dev-password-1"

http = requests.Session()
failures: list[str] = []


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def call(method, path, *, token=None, expected=(200, 201), **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = http.request(method, BASE + path, headers=headers, timeout=15, **kwargs)
    if resp.status_code not in expected:
        sys.exit(f"\nFAILED {method} {path} -> {resp.status_code}\n{resp.text}")
    return resp.json() if resp.content else None


def check(label, actual, expected):
    ok = actual == expected
    print(
        f"  [{'ok' if ok else 'FAIL'}] {label}: {actual}"
        + ("" if ok else f"  (expected {expected})")
    )
    if not ok:
        failures.append(label)


def step(title):
    print(f"\n=== {title} ===")


def discover_from_openapi():
    """Find the register/login paths and the course program enum without hard-coding them."""
    spec = http.get(f"{BASE}/openapi.json", timeout=15).json()
    paths = spec["paths"]
    register = next(p for p in paths if p.endswith("/register"))
    login = next(p for p in paths if p.endswith("/login"))
    program = (
        spec.get("components", {})
        .get("schemas", {})
        .get("CourseProgram", {})
        .get("enum", ["SE"])[0]
    )
    return register, login, program


def register_user(register_path, **fields):
    return call("POST", register_path, json={"password": PASSWORD, **fields})


def login(login_path, email):
    # FastAPI Users' login takes form data, with the email in the "username" field.
    return call("POST", login_path, data={"username": email, "password": PASSWORD})["access_token"]


def student_number():
    return "400" + "".join(random.choices("0123456789", k=6))


def show_projects(course_id, titles):
    for p in call("GET", f"/api/projects?course_id={course_id}"):
        print(
            f"  {titles[p['id']]:<28} status={p['status']:<5} "
            f"slots={p['slots_reserved']}/{p['supervisor_capacity']} (available {p['slots_available']})"
        )


def show_applications(who, token, titles, **params):
    apps = call("GET", "/api/applications", token=token, params=params)
    print(f"  {who} sees {len(apps)} application(s):")
    for a in apps:
        print(f"    - {titles[a['project_id']]:<28} {a['status']}")
    return apps


def get_project(project_id):
    return call("GET", f"/api/projects/{project_id}")


# ---------------------------------------------------------------------------
# the demo
# ---------------------------------------------------------------------------
def main():
    run = uuid.uuid4().hex[:6]
    register_path = "/auth/register"
    login_path = "/auth/login"
    program = "se"
    print(f"register={register_path}  login={login_path}  program={program}  run={run}")

    # --- course -----------------------------------------------------------
    step("1. Create course")
    course_code = f"CAP{run}"
    course = call(
        "POST",
        "/api/courses",
        json={"code": course_code, "name": f"Capstone {run}", "program": program},
    )
    course_id = course["id"]
    print(f"  course {course_code} -> {course_id}")

    # --- users (instructor, TA, supervisor, 2 students) ---------------------
    step("2. Register users")
    emails = {
        "instructor": f"instructor.{run}@example.com",
        "ta": f"ta.{run}@example.com",
        "supervisor": f"supervisor.{run}@example.com",
        "student1": f"student1.{run}@example.com",
        "student2": f"student2.{run}@example.com",
    }
    instructor = register_user(
        register_path,
        email=emails["instructor"],
        first_name="Ida",
        last_name="Instructor",
        role="instructor",
        course_codes=[course_code],
    )
    ta = register_user(
        register_path,
        email=emails["ta"],
        first_name="Tara",
        last_name="Assistant",
        role="ta",
        course_code=course_code,
    )
    supervisor = register_user(
        register_path,
        email=emails["supervisor"],
        first_name="Sam",
        last_name="Supervisor",
        role="supervisor",
    )
    student1 = register_user(
        register_path,
        email=emails["student1"],
        first_name="Stu",
        last_name="One",
        role="student",
        student_number=student_number(),
        course_code=course_code,
    )
    student2 = register_user(
        register_path,
        email=emails["student2"],
        first_name="Sue",
        last_name="Two",
        role="student",
        student_number=student_number(),
        course_code=course_code,
    )
    for name, u in [
        ("instructor", instructor),
        ("ta", ta),
        ("supervisor", supervisor),
        ("student1", student1),
        ("student2", student2),
    ]:
        print(f"  {name:<10} -> {u['id']}")

    tokens = {name: login(login_path, email) for name, email in emails.items()}
    print("  logged in all users")

    # --- team -------------------------------------------------------------
    step("3. Create team (student1 + student2)")
    team = call(
        "POST",
        "/api/teams",
        json={
            "name": f"Team Amazing {run}",
            "course_id": course_id,
            "student_ids": [student1["id"], student2["id"]],
        },
    )
    print(f"  team {team['name']} -> {team['id']} with {len(team['members'])} members")

    # --- projects ---------------------------------------------------------
    step("4. Supervisor creates 3 projects")
    specs = [
        ("Automated Assembly Line", 1),
        ("Autonomous Waste Sorting System", 2),
        ("Smart Campus Navigator", 1),
    ]
    projects = []
    for title, capacity in specs:
        p = call(
            "POST",
            f"/api/projects?supervisor_id={supervisor['id']}",
            json={
                "title": title,
                "background": f"Background for {title}.",
                "course_id": course_id,
                "supervisor_capacity": capacity,
            },
        )
        projects.append(p)
    titles = {p["id"]: p["title"] for p in projects}
    p1, p2, _p3 = projects
    show_projects(course_id, titles)

    # --- apply ------------------------------------------------------------
    step("5. Team applies to Assembly Line and Waste Sorting (student1 acts for the team)")
    apps = {}
    for p in (p1, p2):
        apps[p["id"]] = call(
            "POST",
            f"/api/applications?student_id={student1['id']}",
            json={"team_id": team["id"], "project_id": p["id"]},
        )
        check(f"application to {p['title']}", apps[p["id"]]["status"], "applied")
    app1, app2 = apps[p1["id"]], apps[p2["id"]]
    check("no slots used by applying (project 1)", get_project(p1["id"])["slots_reserved"], 0)

    # --- supervisor accepts -----------------------------------------------
    step("6. Supervisor accepts the team on Assembly Line (capacity 1)")
    seen = show_applications("supervisor", tokens["supervisor"], titles)
    check("supervisor sees both applications", len(seen), 2)
    accepted = call("POST", f"/api/applications/{app1['id']}/accept", token=tokens["supervisor"])
    check("application status", accepted["status"], "supervisor_accepts")
    proj1 = get_project(p1["id"])
    check("slots reserved on Assembly Line", proj1["slots_reserved"], 1)
    check("Assembly Line status", proj1["status"].lower(), "full")
    show_projects(course_id, titles)

    # --- team agrees ------------------------------------------------------
    step("7. Team agrees (competing application should be withdrawn)")
    agreed = call("POST", f"/api/applications/{app1['id']}/agree", token=tokens["student1"])
    check("application status", agreed["status"], "agreed")
    check("slots on Assembly Line unchanged", get_project(p1["id"])["slots_reserved"], 1)
    other = call("GET", f"/api/applications/{app2['id']}", token=tokens["student1"])
    check("competing application on Waste Sorting", other["status"], "declined_or_withdrawn")

    # --- submit and approve -------------------------------------------------
    step("8. Team submits the project for review")
    submitted = call("POST", f"/api/applications/{app1['id']}/submit", token=tokens["student1"])
    check("application status", submitted["status"], "team_project_under_review")

    step("9. Instructor approves")
    approved = call("POST", f"/api/applications/{app1['id']}/approve", token=tokens["instructor"])
    check("application status", approved["status"], "approved")

    # --- final state ------------------------------------------------------
    step("10. Final state")
    show_projects(course_id, titles)
    show_applications("instructor", tokens["instructor"], titles, course_id=course_id)
    show_applications("TA", tokens["ta"], titles, course_id=course_id)
    show_applications("supervisor", tokens["supervisor"], titles)
    mate = show_applications("student2 (teammate)", tokens["student2"], titles)
    check(
        "teammate sees the approved application", any(a["status"] == "approved" for a in mate), True
    )

    print(
        "\n"
        + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} CHECK(S) FAILED: {failures}")
    )
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
