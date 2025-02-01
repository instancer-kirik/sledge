defmodule Sledge.Application do
  use Application

  def start(_type, _args) do
    children = [
      SledgeWeb.Endpoint,
      {Sledge.Browser.SupervisorPool, []},
      {Sledge.Security.Supervisor, []},
      {Phoenix.PubSub, name: Sledge.PubSub},
      {Sledge.BrowserState, []}
    ]

    opts = [strategy: :one_for_one, name: Sledge.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
