1. **Make currency cards narrower**
   - Edit `app/templates/dashboard.html` to change `.cards-grid` CSS from `minmax(180px, 1fr)` to `minmax(150px, 1fr)` so that the Binance card fits properly on desktop view.
2. **Save currency updates as a historical log**
   - Modify `app/services/storage.py` to remove the `UNIQUE` constraint on the `date` column. This transforms the database into an append-only historical table where every update is recorded, enabling precise historical consumption.
   - Implement an automatic migration in `_init_db` to rename the old table, create the new table without the `UNIQUE(date)` constraint, and copy the data over.
   - Update `storage.py` to replace `upsert` with `add_record` that strictly `INSERT`s data instead of overwriting the day's record. Update `get_by_date` to fetch the latest entry of the requested date.
   - Update `app/main.py` and `app/routers/api.py` to use `storage.add_record(rates)`.
3. **Complete pre-commit steps**
   - Ensure proper testing, verification, review, and reflection are done by running required commands before submission.
4. **Submit changes**
   - Once all tests and checks pass, submit the branch with a descriptive commit message.
