.. _topics_overriding:

#######################
Overriding Dependencies
#######################

A powerful feature of Dependency Injection frameworks like Picodi is the ability to **override** dependencies. This means you can replace the provider function for a specific dependency with a different one at runtime, without modifying the code that consumes the dependency.

**************************
Why Override Dependencies?
**************************

Overriding is essential for several scenarios:

*   **Testing:** This is the most common use case. You can replace dependencies that interact with external systems (databases, APIs, file systems) with mock objects or test doubles. This allows you to write fast, isolated unit tests without relying on real external resources.
*   **Environment Configuration:** You might have different implementations for different environments. For example, a dependency that sends emails could use a real SMTP server in production but a simple console logger or a fake server in development and testing environments.
*   **Feature Flags:** Swap dependency implementations based on runtime feature flags to enable or disable certain functionalities.
*   **Abstract Dependencies:** Define an "abstract" dependency provider (perhaps raising `NotImplementedError`) and require specific implementations to be provided via overrides in different application contexts.

****************************************
How to Override: ``registry.override()``
****************************************

Picodi provides the :meth:`picodi.Registry.override` method on the ``registry`` object to manage overrides. It offers flexibility by working as both a context manager and a decorator.

Using ``override`` as a Context Manager
=======================================

This is the recommended approach for temporary overrides, especially within tests or specific code blocks. The override is active only within the ``with`` block and is automatically removed upon exiting.

.. code-block:: python

    from picodi import registry, Provide, inject


    # --- Original Dependencies ---
    def get_database_url() -> str:
        print("Original: Using Production DB URL")
        return "prod_db_url"


    def get_email_sender() -> callable:
        print("Original: Using Real Email Sender")

        def send(to, subject, body):
            print(f"RealEmail: Sending to {to} - {subject}")

        return send


    # --- Test/Alternative Dependencies ---
    def get_test_database_url() -> str:
        print("Override: Using Test DB URL")
        return "test_db_url"


    def get_mock_email_sender() -> callable:
        print("Override: Using Mock Email Sender")
        sent_emails = []

        def send(to, subject, body):
            print(f"MockEmail: Pretending to send to {to} - {subject}")
            sent_emails.append({"to": to, "subject": subject, "body": body})

        # Attach the log for inspection in tests
        send.sent_emails = sent_emails
        return send


    # --- Service Using Dependencies ---
    @inject
    def register_user(
        username: str,
        db_url: str = Provide(get_database_url),
        send_email: callable = Provide(get_email_sender),
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
    mock_sender_provider = get_mock_email_sender()  # Get the provider function
    with registry.override(get_database_url, get_test_database_url), registry.override(
        get_email_sender, mock_sender_provider
    ):
        register_user("full_mock_user")
        # We can inspect the mock
        assert len(mock_sender_provider.sent_emails) == 1
        assert mock_sender_provider.sent_emails[0]["to"] == "full_mock_user@example.com"

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

Using ``override`` as a Decorator
=================================

You can also apply ``override`` as a decorator directly onto the overriding function. This registers the override more permanently (it persists until explicitly cleared).

.. code-block:: python

    from picodi import registry, Provide, inject


    def get_original_setting():
        return "Original Value"


    @inject
    def use_setting(setting=Provide(get_original_setting)):
        print(f"Using setting: {setting}")


    # --- Apply override using decorator ---
    @registry.override(get_original_setting)
    def get_overridden_setting():
        return "Decorated Override Value"


    print("--- Calling with decorator override active ---")
    use_setting()

    # Override persists
    print("\n--- Calling again ---")
    use_setting()

    # --- Manually clear the override ---
    print("\n--- Clearing override ---")
    registry.override(get_original_setting, None)  # Pass None as the second arg

    print("\n--- Calling after clear ---")
    use_setting()

**Output:**

.. code-block:: text

    --- Calling with decorator override active ---
    Using setting: Decorated Override Value

    --- Calling again ---
    Using setting: Decorated Override Value

    --- Clearing override ---

    --- Calling after clear ---
    Using setting: Original Value

While the decorator approach works, the context manager is generally preferred for test isolation and clarity, as it automatically handles cleanup.

********************
Clearing Overrides
********************

As shown above, overrides applied via the decorator persist. You need to clear them manually:

*   **Clear a specific override:**
    ``registry.override(original_dependency, None)``
*   **Clear all overrides:**
    ``registry.clear_overrides()``

Clearing overrides is crucial in test suites to prevent state leakage between tests. The Picodi ``pytest`` plugin handles this automatically (see :ref:`topics_testing`).

****************
Key Takeaways
****************

*   Use ``registry.override(original, new_provider)`` to replace dependency implementations.
*   The context manager (``with registry.override(...)``) is ideal for temporary overrides (like in tests) as it handles cleanup automatically.
*   The decorator (``@registry.override(original)``) creates persistent overrides that require manual clearing.
*   Clear specific overrides with ``registry.override(original, None)`` or all overrides with ``registry.clear_overrides()``.
*   Overriding is fundamental for testing and configuring applications based on environment or features.

Next, let's look at managing the overall application lifecycle, including dependency initialization and shutdown, using :ref:`Lifespan Management <topics_lifespan>`.
