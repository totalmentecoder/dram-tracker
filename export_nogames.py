from pipeline import init_db, build_dashboard_nogames
conn = init_db()
fig = build_dashboard_nogames(conn)
fig.write_html("dashboard_nogames.html", include_plotlyjs="cdn")
fig.show()
conn.close()