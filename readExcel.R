library(gdata)

chr1 = read.xls("C:\\Users\\bishopp\\Dropbox\\Sailing cmte\\Handicapping\\2014-15 season\\RPNYC results\\Championship Series.xls",sheet="Chr1")

chr1$X <- gsub(':', '', chr1$X)

write.csv(chr1, "C:\\Users\\bishopp\\Dropbox\\Sailing cmte\\Handicapping\\2014-15 season\\Raw CSVs\\chr1.csv", row.names=FALSE)

# Extra bits of R code

# source("readExcel.R")  # command to read and execute an R script

# mydata$Date <- NULL  # Delete the column called Date from the data frame called mydata

# mydata <- mydata[-c(12:18), ] # delete rows called 12 thru 18 from the data frame called mydata

# http://www.statmethods.net/management/subset.html

