#!/bin/bash
DB=/opt/whovoted/data/whovoted.db

echo "=== 2024 Flips (voters who switched party from their previous election) ==="
sqlite3 "$DB" "
SELECT ve_current.party_voted as to_party, ve_prev.party_voted as from_party, COUNT(*) as cnt
FROM voter_elections ve_current
JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
WHERE ve_current.election_date = '2024-03-05'
  AND ve_prev.election_date = (
      SELECT MAX(ve2.election_date) FROM voter_elections ve2
      WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
  AND ve_current.party_voted != ve_prev.party_voted
  AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
GROUP BY ve_current.party_voted, ve_prev.party_voted;
"

echo ""
echo "=== What previous election did 2024 flippers come from? ==="
sqlite3 "$DB" "
SELECT ve_prev.election_date as prev_election, COUNT(*) as cnt
FROM voter_elections ve_current
JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
WHERE ve_current.election_date = '2024-03-05'
  AND ve_prev.election_date = (
      SELECT MAX(ve2.election_date) FROM voter_elections ve2
      WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
  AND ve_current.party_voted != ve_prev.party_voted
  AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
GROUP BY ve_prev.election_date
ORDER BY ve_prev.election_date;
"

echo ""
echo "=== Total 2024 voters by party ==="
sqlite3 "$DB" "SELECT party_voted, COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted != '' GROUP BY party_voted;"

echo ""
echo "=== Total 2022 voters by party ==="
sqlite3 "$DB" "SELECT party_voted, COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted != '' GROUP BY party_voted;"

echo ""
echo "=== How many 2024 voters also voted in 2022? ==="
sqlite3 "$DB" "
SELECT COUNT(*) FROM voter_elections ve24
JOIN voter_elections ve22 ON ve24.vuid = ve22.vuid
WHERE ve24.election_date='2024-03-05' AND ve22.election_date='2022-03-01';
"
