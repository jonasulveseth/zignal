class IndexController < ApplicationController
  allow_unauthenticated_access only: %i[ index ]

  def index
  end

  def mypage
  end
end
