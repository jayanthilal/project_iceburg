from iceburg.web.app import create_app as create_app_web


def run_web(port=5000, debug=False):
    app = create_app_web(debug=debug)
    app.run(host='0.0.0.0', debug=debug, port=port)


if __name__ == '__main__':
    run_web()
