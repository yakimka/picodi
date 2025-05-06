.. _topics_overriding:

#######################
Overriding Dependencies
#######################

A powerful feature of Dependency Injection frameworks like Picodi is the ability to **override** dependencies.
This means you can replace the provider function for a specific dependency with a different one at runtime,
without modifying the code that consumes the dependency.

**************************
Why Override Dependencies?
**************************

Overriding is essential for several scenarios:

*   **Testing:** This is the most common use case. You can replace dependencies that interact with external systems
    (databases, APIs, file systems) with mock objects or test doubles.
    This allows you to write fast, isolated tests without relying on real external resources.
*   **Abstract Dependencies:** Define an "abstract" dependency provider (perhaps raising ``NotImplementedError``)
    and require specific implementations to be provided via overrides in different application contexts.

****************************************
How to Override: ``registry.override()``
****************************************

Picodi provides the :meth:`picodi.Registry.override` method on the ``registry`` object to manage overrides.

Using ``override`` as a Context Manager
=======================================

This is the recommended approach for temporary overrides, especially within tests or specific code blocks.
The override is active only within the ``with`` block and is automatically removed upon exiting.

.. code-block:: python

    from typing import Callable

    from picodi import registry, Provide, inject


    # --- Original Dependencies ---
    def get_database_url() -> str:
        print("Original: Using Production DB URL")
        return "prod_db_url"


    def get_email_sender() -> Callable:
        print("Original: Using Real Email Sender")

        def send(to, subject, body):
            print(f"RealEmail: Sending to {to} - {subject}")

        return send


    # --- Test/Alternative Dependencies ---
    def get_test_database_url() -> str:
        print("Override: Using Test DB URL")
        return "test_db_url"


    #  log for inspection in tests
    sent_emails = []


    def get_mock_email_sender() -> Callable:
        print("Override: Using Mock Email Sender")

        def send(to, subject, body):
            print(f"MockEmail: Pretending to send to {to} - {subject}")
            sent_emails.append({"to": to, "subject": subject, "body": body})

        return send


    # --- Service Using Dependencies ---
    @inject
    def register_user(
        username: str,
        db_url: str = Provide(get_database_url),
        send_email: Callable = Provide(get_email_sender),
    ):
        print(f"Service: Registering {username} using DB {db_url}")
        # ... database logic using db_url ...
        send_email(
            to=f"{username}@example.com", subject="Welcome!", body="Thanks for registering."
        )
        print(f"Service: User {username} registered.")


    # --- Using Overrides in a Test-like Scenario ---
    print("--- Running with Production Defaults ---")
    register_user("prod_user")

    print("\n--- Running with Test Overrides (Context Manager) ---")
    with registry.override(get_database_url, get_test_database_url):
        # Override only the database for this block
        register_user("test_db_user")

    print("\n--- Running with Multiple Overrides ---")
    with registry.override(get_database_url, get_test_database_url), registry.override(
        get_email_sender, get_mock_email_sender
    ):
        register_user("full_mock_user")
        # We can inspect the mock
        assert len(sent_emails) == 1
        assert sent_emails[0]["to"] == "full_mock_user@example.com"

    print("\n--- Running After Context Managers Exit ---")
    # Overrides are automatically cleared
    register_user("prod_user_again")

**Output:**

.. code-block:: text

    --- Running with Production Defaults ---
    Original: Using Production DB URL
    Original: Using Real Email Sender
    Service: Registering prod_user using DB prod_db_url
    RealEmail: Sending to prod_user@example.com - Welcome!
    Service: User prod_user registered.

    --- Running with Test Overrides (Context Manager) ---
    Override: Using Test DB URL
    Original: Using Real Email Sender
    Service: Registering test_db_user using DB test_db_url
    RealEmail: Sending to test_db_user@example.com - Welcome!
    Service: User test_db_user registered.

    --- Running with Multiple Overrides ---
    Override: Using Test DB URL
    Override: Using Mock Email Sender
    Service: Registering full_mock_user using DB test_db_url
    MockEmail: Pretending to send to full_mock_user@example.com - Welcome!
    Service: User full_mock_user registered.

    --- Running After Context Managers Exit ---
    Original: Using Production DB URL
    Original: Using Real Email Sender
    Service: Registering prod_user_again using DB prod_db_url
    RealEmail: Sending to prod_user_again@example.com - Welcome!
    Service: User prod_user_again registered.

******************
Clearing Overrides
******************

If you apply override not using a context manager,
but as a function call  - you need to clear them manually:

*   **Clear a specific override:**
    ``registry.override(original_dependency, None)``
*   **Clear all overrides:**
    ``registry.clear_overrides()``

Clearing overrides is crucial in test suites to prevent state leakage between tests.
The Picodi ``pytest`` plugin handles this automatically (see :ref:`topics_testing`).

*************
Key Takeaways
*************

*   Use ``registry.override(original, new_provider)`` to replace dependency implementations.
*   The context manager (``with registry.override(...)``) is ideal for temporary overrides (like in tests) as it handles cleanup automatically.
*   Clear specific overrides with ``registry.override(original, None)`` or all overrides with ``registry.clear_overrides()``.
*   Overriding is fundamental for testing.

Next, let's look at managing the overall application lifecycle,
including dependency initialization and shutdown, using :ref:`Lifespan Management <topics_lifespan>`.
