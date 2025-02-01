defmodule Sledge.Security.ContentSecurity do
  use GenServer

  @sandbox_options %{
    "allow-scripts" => false,
    "allow-same-origin" => false,
    "allow-popups" => false,
    "allow-modals" => false,
    "allow-forms" => false
  }

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def sanitize_content(content, options \\ []) do
    GenServer.call(__MODULE__, {:sanitize_content, content, options})
  end

  @impl true
  def handle_call({:sanitize_content, content, options}, _from, state) do
    sanitized = content
      |> remove_dangerous_elements()
      |> apply_content_security_policy()
      |> sandbox_content(options)

    {:reply, sanitized, state}
  end

  defp remove_dangerous_elements(content) do
    # Remove potentially harmful HTML elements and attributes
    HtmlSanitizer.sanitize(content, Sledge.Security.SanitizerRules)
  end

  defp apply_content_security_policy(content) do
    # Inject CSP meta tag
    csp = build_csp_policy()
    inject_meta_csp(content, csp)
  end

  defp sandbox_content(content, options) do
    sandbox_attrs = build_sandbox_attributes(options)
    wrap_in_sandbox(content, sandbox_attrs)
  end
end
