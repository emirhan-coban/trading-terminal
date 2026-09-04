from terminal.api import cursor_page

def test_cursor_page_is_stable():
 rows=[{"id":str(n)} for n in range(5)]
 first,cursor=cursor_page(rows,None,2)
 second,next_cursor=cursor_page(rows,cursor,2)
 last,end=cursor_page(rows,next_cursor,2)
 assert [x["id"] for x in first+second+last]==["0","1","2","3","4"]
 assert end is None
