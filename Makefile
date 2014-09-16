APP = afternoon-beach-7789

update:
	git push heroku master

restart:
	heroku restart --app $(APP)

logs:
	heroku logs -t --app $(APP)

psql:
	heroku pg:psql --app $(APP)

config_set:
	heroku config:set INTERESTED_CLUSTERS="scinet mp2 colosse guillimin lattice nestor parallel orcinus" --app $(APP)

# heroku pgbackups:capture HEROKU_POSTGRESQL_RED --expire --app $(APP); \

BACKUP_DIR = afternoon.backup
backup:
	BK=$$(heroku pgbackups --app $(APP) | tail -n1 | awk '{print $$1}');  \
	URL=$$(heroku pgbackups:url $${BK} --app $(APP));                     \
        curl -o $(BACKUP_DIR)/$${BK}.dump $${URL}


# To export data from the database to local.csv, connect to the server using
# "make psql", and refer to the following example
# \copy (select * from usage where clustername='colosse' and username='pomeslab' and created > '2013-01-01' order by created) to 'colosse.csv' with CSV HEADER;
