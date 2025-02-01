defmodule Sledge.Security.FonceIntegration do
  use GenServer
  require Logger

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    # Subscribe to Fonce security events
    Phoenix.PubSub.subscribe(Fonce.PubSub, "security_events")
    {:ok, %{blocked_urls: MapSet.new()}}
  end

  @impl true
  def handle_info({:security_event, :malicious_url_detected, data}, state) do
    # Update browser security rules based on Fonce detections
    new_blocked = MapSet.put(state.blocked_urls, data.url)
    Sledge.Security.BrowserSecurity.update_blacklist(new_blocked)
    {:noreply, %{state | blocked_urls: new_blocked}}
  end
end
