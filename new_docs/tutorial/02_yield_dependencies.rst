.. _tutorial_yield_dependencies:

##################################
Tutorial: 02 - Yield Dependencies
##################################

Some resources, like files or network connections, need to be properly closed or released after use.
Picodi allows you to manage the setup and teardown of such dependencies using generator functions with a single `yield`.

*******************************
The Need for Setup and Teardown
*******************************

Imagine a dependency that provides a temporary file for writing data.
This file needs to be created before use and deleted afterward.

A simple ``return`` statement isn't enough because we need to
execute cleanup code *after* the dependency has been used by the function that injected it.

****************************************
Using ``yield`` for Lifecycle Management
****************************************

Picodi leverages Python's generators for this.
If a dependency function is a generator that yields exactly once,
Picodi treats it like a context manager (similar to those created with :func:`python:contextlib.contextmanager`).

*   The code **before** the ``yield`` is executed during the setup phase (when the dependency is first needed).
*   The value **yielded** is the actual dependency instance provided to the injecting function.
*   The code **after** the ``yield`` is executed during the teardown phase (after the function that injected the dependency finishes).

Let's modify our example to use a temporary file managed by a yield dependency.

.. testcode:: yield_deps

    # dependencies.py
    import tempfile
    import os


    # We don't need @inject or Provide here for get_temp_file_path
    # because it doesn't depend on any other dependencies.
    def get_temp_file_path():
        """Provides a path to a temporary file and cleans it up afterwards."""
        tf = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".txt")
        file_path = tf.name
        print(f"Setup: Created temp file: {file_path}")
        tf.close()  # Close the file handle, but the file remains

        try:
            yield file_path  # Provide the path
        finally:
            # Teardown: This code runs after the injecting function finishes
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Teardown: Removed temp file: {file_path}")
            else:
                print(
                    f"Teardown: Temp file already removed: {file_path}"
                )  # Should not happen in normal flow


    # services.py
    from picodi import Provide, inject
    from dependencies import get_temp_file_path


    @inject
    def write_to_temp_file(
        content: str,
        temp_file: str = Provide(get_temp_file_path),  # Inject the yielded path
    ) -> None:
        """Writes content to a temporary file provided by a dependency."""
        print(f"Service: Writing to {temp_file}")
        with open(temp_file, "a") as f:
            f.write(content + "\n")
        print(f"Service: Finished writing to {temp_file}")


    # main.py
    from services import write_to_temp_file

    print("Main: Calling service the first time.")
    write_to_temp_file("Hello from Picodi!")
    print("Main: Service call finished.")

    print("\nMain: Calling service the second time.")
    write_to_temp_file("Another message.")
    print("Main: Service call finished.")

**Explanation:**

1.  **get_temp_file_path:** This function now uses ``yield``.
    It creates a temporary file, yields its path, and then removes the file in a ``finally`` block.
    The :func:`python:contextlib.contextmanager` decorator is used here for clarity and standard practice,
    although Picodi only requires the single ``yield`` structure.
2.  **Injection:** ``write_to_temp_file`` injects the *yielded value* (the file path string) from ``get_temp_file_path``.
3.  **Execution Flow:** When ``write_to_temp_file`` is called:

    *   Picodi calls ``get_temp_file_path``.
    *   The code before ``yield`` runs (file created).
    *   The file path is yielded and injected into ``write_to_temp_file``.
    *   The body of ``write_to_temp_file`` executes (writing to the file).
    *   After ``write_to_temp_file`` finishes, Picodi resumes the ``get_temp_file_path`` generator.
    *   The code after ``yield`` (in the ``finally`` block) runs (file removed).

**Output:**

.. testoutput:: yield_deps

    Main: Calling service the first time.
    Setup: Created temp file: .../tmp.../tmpwt0haf9v.txt
    Service: Writing to .../tmp.../tmpwt0haf9v.txt
    Service: Finished writing to .../tmp.../tmpwt0haf9v.txt
    Teardown: Removed temp file: .../tmp.../tmpwt0haf9v.txt
    Main: Service call finished.

    Main: Calling service the second time.
    Setup: Created temp file: .../tmp.../tmpeiljxw8u.txt
    Service: Writing to .../tmp.../tmpeiljxw8u.txt
    Service: Finished writing to .../tmp.../tmpeiljxw8u.txt
    Teardown: Removed temp file: .../tmp.../tmpeiljxw8u.txt
    Main: Service call finished.

*(Note: The exact temporary file paths will vary)*

As you can see, the setup code runs before the service function, and the teardown code runs after it finishes,
ensuring the resource is managed correctly.
A new temporary file is created and destroyed for each call because we are still using the default :class:`~picodi.NullScope`.

***********
Next Steps
***********

Now that you know how to manage dependency lifecycles with ``yield``,
let's explore how to control *how often* dependencies are created using :ref:`Scopes <tutorial_scopes>`.
