defmodule Sledge.Security.BrowserSecurity do
  use GenServer
  require Logger

  @blocked_schemes ["file", "ftp", "data"]
  @safe_browsing_api "https://safebrowsing.googleapis.com/v4/"

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def check_url(url) do
    GenServer.call(__MODULE__, {:check_url, url})
  end

  @impl true
  def handle_call({:check_url, url}, _from, state) do
    uri = URI.parse(url)

    result = with :ok <- check_scheme(uri.scheme),
                  :ok <- check_safe_browsing(url),
                  :ok <- check_local_blacklist(url) do
      :ok
    end

    case result do
      :ok ->
        {:reply, :ok, state}
      {:error, reason} = error ->
        notify_fonce(url, reason)
        {:reply, error, state}
    end
  end

  defp check_scheme(scheme) when scheme in @blocked_schemes do
    {:error, :blocked_scheme}
  end
  defp check_scheme(_), do: :ok

  defp check_safe_browsing(url) do
    # Interface with Google Safe Browsing API
    case HTTPoison.post(@safe_browsing_api <> "threatMatches:find", build_lookup_body(url)) do
      {:ok, %{status_code: 200, body: body}} ->
        case Jason.decode!(body) do
          %{"matches" => [_ | _]} -> {:error, :malicious_url}
          _ -> :ok
        end
      _ ->
        :ok # Fail open if API is unavailable
    end
  end

  defp notify_fonce(url, reason) do
    # Send threat info to Fonce for monitoring
    Phoenix.PubSub.broadcast(
      Fonce.PubSub,
      "security_events",
      {:browser_security_event, %{
        type: :malicious_url,
        url: url,
        reason: reason,
        timestamp: DateTime.utc_now()
      }}
    )
  end
end
