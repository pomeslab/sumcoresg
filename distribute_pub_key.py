import time
import util

# This is a really bad idea, doing passwordless SSHing to many locations.
# It does work though...
def main():
    accounts = [
        ['TEST', 'login.scinet.utoronto.ca'],
        ['TEST', 'colosse.clumeq.ca'],
        ['TEST', 'guillimin.clumeq.ca'],

        ['TEST', 'pomes-mp2.ccs.usherbrooke.ca'],
        ['TEST', 'orca.sharcnet.ca'],

        ['TEST', 'nestor.westgrid.ca'],
        ['TEST', 'lattice.westgrid.ca'],
        ['TEST', 'parallel.westgrid.ca'],
        ['TEST', 'orcinus.westgrid.ca'],
        ]

    new_key = open(".sumcoresgk.pub").readline().strip()

    auth_keyf = "~/.ssh/authorized_keys"
    cmd = ('sed -i -e "/heroku/d" '
           '-e "/^$/d" {0}'
           '; '
           'printf "\n{1}\n" >> {0}'.format(auth_keyf, new_key))

    # cmd = "ls"


    for (acc, cluster) in accounts:
        print cluster,
        btime = time.time()
        output = util.sshexec(cluster, acc, cmd, rsa_key_file="/Users/redacted/.ssh/id_rsa")
        print output
        etime = time.time()
        print etime - btime
        # subprocess.call("ssh {0}@{1} ls".format(acc, cluster), shell=True)


if __name__ == "__main__":
    main()
