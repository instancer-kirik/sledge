from pathlib import Path
import subprocess
import os
import http.server
import socketserver
import threading
import shutil

class GleamProjectHandler:
    def __init__(self, project_dir):
        self.project_dir = Path(project_dir)
        self.build_dir = self.project_dir / "build/dev/javascript"
        self.static_dir = self.build_dir / "priv/static"
        
    def build_project(self):
        """Build the Gleam project"""
        try:
            # Clean and rebuild
            subprocess.run(["gleam", "clean"], cwd=self.project_dir, check=True)
            subprocess.run(["gleam", "build", "--target", "javascript"], 
                         cwd=self.project_dir, check=True)
            
            # Ensure static directory exists
            self.static_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy built JS files to static directory
            for js_file in self.build_dir.rglob("*.mjs"):
                rel_path = js_file.relative_to(self.build_dir)
                dest = self.static_dir / rel_path.name
                shutil.copy2(js_file, dest)
                
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error building Gleam project: {e}")
            return False

    def create_index_html(self, module_name):
        """Create index.html for the Gleam app"""
        index_content = f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Gleam App</title>
    </head>
    <body>
        <div id="app"></div>
        <script type="module">
            import {{ main }} from '/priv/static/{module_name}.mjs';
            main();
        </script>
    </body>
</html>"""
        
        index_path = self.build_dir / "index.html"
        index_path.write_text(index_content)
        return index_path

    def serve_project(self, port=8000):
        """Serve the built project"""
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(self.build_dir), **kwargs)

        def run_server():
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(f"🌐 Serving Gleam app at http://localhost:{port}")
                httpd.serve_forever()

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        return f"http://localhost:{port}" 